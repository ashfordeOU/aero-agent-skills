#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.4.3 detailed-requirement leaf.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_detailed_emc_verification_requirements.py
"""

import unittest

from e20_detailed_emc_verification_requirements_logic import (
    DEFAULT_AMBIENT_SEPARATION_DB,
    DETECTORS,
    VERIFICATION_CATEGORIES,
    ambient_is_quiet_enough,
    ambient_separation_db,
    build_requirement_index,
    coverage_gaps,
    disposition,
    evaluate_run,
    max_allowed_step,
    meets_minimum_dwell,
    normalise_referenced_requirement,
    normalise_verification_run,
    per_step_dwell,
    review_campaign,
    step_count,
    total_sweep_dwell,
)


def requirement(**over):
    record = {
        "id": "CE-01",
        "category": "conducted-emission",
        "start_hz": 1.0e4,
        "stop_hz": 1.0e7,
        "bandwidth_hz": 1000.0,
        "max_step_fraction": 0.5,
        "min_step_dwell_s": 1.0e-5,
        "min_total_dwell_s": 12.3,
        "detector": "peak",
        "limit_db": 33.3,
        "ambient_separation_db": 6.0,
    }
    record.update(over)
    return record


def run(**over):
    record = {
        "id": "RUN-1",
        "reference": "CE-01",
        "detector": "peak",
        "measured_db": 31.1,
        "ambient_db": 27.3,
        "uncertainty_db": 2.2,
        "segments": [
            {"start_hz": 1.0e4, "stop_hz": 1.0e5, "step_hz": 500.0, "dwell_s": 4.1},
            {"start_hz": 1.0e5, "stop_hz": 1.0e6, "step_hz": 500.0, "dwell_s": 4.1},
            {"start_hz": 1.0e6, "stop_hz": 1.0e7, "step_hz": 500.0, "dwell_s": 4.1},
        ],
    }
    record.update(over)
    return record


class RequirementNormalisation(unittest.TestCase):
    def test_requirement_is_canonicalised(self):
        req = normalise_referenced_requirement(requirement())
        self.assertEqual(req["id"], "CE-01")
        self.assertAlmostEqual(req["limit_db"], 33.3, places=9)

    def test_ambient_separation_defaults_when_unstated(self):
        record = requirement()
        del record["ambient_separation_db"]
        req = normalise_referenced_requirement(record)
        self.assertAlmostEqual(
            req["ambient_separation_db"], DEFAULT_AMBIENT_SEPARATION_DB, places=9
        )

    def test_every_category_is_accepted(self):
        for category in VERIFICATION_CATEGORIES:
            req = normalise_referenced_requirement(requirement(category=category))
            self.assertEqual(req["category"], category)

    def test_every_detector_is_accepted(self):
        for detector in DETECTORS:
            req = normalise_referenced_requirement(requirement(detector=detector))
            self.assertEqual(req["detector"], detector)

    def test_empty_requirement_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(id="   "))

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(category="radiated-noise"))

    def test_inverted_frequency_range_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(start_hz=1.0e7, stop_hz=1.0e4))

    def test_zero_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(bandwidth_hz=0.0))

    def test_step_fraction_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(max_step_fraction=1.5))

    def test_zero_step_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(max_step_fraction=0.0))

    def test_unknown_detector_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(detector="eyeball"))

    def test_negative_total_dwell_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement(requirement(min_total_dwell_s=-1.0))

    def test_non_mapping_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_referenced_requirement("CE-01")

    def test_duplicate_requirement_id_is_rejected(self):
        with self.assertRaises(ValueError):
            build_requirement_index([requirement(), requirement()])

    def test_empty_requirement_set_is_rejected(self):
        with self.assertRaises(ValueError):
            build_requirement_index([])


class RunNormalisation(unittest.TestCase):
    def test_segments_are_ordered_by_start_frequency(self):
        record = run()
        record["segments"].reverse()
        normalised = normalise_verification_run(record)
        starts = [segment["start_hz"] for segment in normalised["segments"]]
        self.assertEqual(starts, sorted(starts))

    def test_empty_run_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(id=""))

    def test_run_without_a_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(reference="   "))

    def test_unknown_run_detector_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(detector="thumb"))

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(uncertainty_db=-1.0))

    def test_missing_segment_list_is_rejected(self):
        record = run()
        del record["segments"]
        with self.assertRaises(ValueError):
            normalise_verification_run(record)

    def test_empty_segment_list_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(segments=[]))

    def test_segment_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(segments=["10 kHz to 100 kHz"]))

    def test_inverted_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(
                run(segments=[{"start_hz": 1.0e5, "stop_hz": 1.0e4, "step_hz": 10.0, "dwell_s": 1.0}])
            )

    def test_zero_dwell_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(
                run(segments=[{"start_hz": 1.0e4, "stop_hz": 1.0e5, "step_hz": 10.0, "dwell_s": 0.0}])
            )

    def test_non_numeric_measured_level_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_verification_run(run(measured_db="31 dB"))


class CoverageGeometry(unittest.TestCase):
    def test_full_coverage_leaves_no_gap(self):
        segments = normalise_verification_run(run())["segments"]
        self.assertEqual(coverage_gaps(segments, 1.0e4, 1.0e7), [])

    def test_an_unswept_upper_band_is_a_gap(self):
        segments = normalise_verification_run(run())["segments"][:2]
        gaps = coverage_gaps(segments, 1.0e4, 1.0e7)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1.0e6, places=6)
        self.assertAlmostEqual(gaps[0][1], 1.0e7, places=6)

    def test_an_unswept_lower_band_is_a_gap(self):
        segments = normalise_verification_run(run())["segments"][1:]
        gaps = coverage_gaps(segments, 1.0e4, 1.0e7)
        self.assertAlmostEqual(gaps[0][0], 1.0e4, places=6)
        self.assertAlmostEqual(gaps[0][1], 1.0e5, places=6)

    def test_a_hole_between_two_segments_is_a_gap(self):
        segments = [
            {"start_hz": 1.0e4, "stop_hz": 1.0e5, "step_hz": 10.0, "dwell_s": 1.0},
            {"start_hz": 1.0e6, "stop_hz": 1.0e7, "step_hz": 10.0, "dwell_s": 1.0},
        ]
        gaps = coverage_gaps(segments, 1.0e4, 1.0e7)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 1.0e5, places=6)

    def test_overlapping_segments_do_not_manufacture_a_gap(self):
        segments = [
            {"start_hz": 1.0e4, "stop_hz": 5.0e6, "step_hz": 10.0, "dwell_s": 1.0},
            {"start_hz": 1.0e6, "stop_hz": 1.0e7, "step_hz": 10.0, "dwell_s": 1.0},
        ]
        self.assertEqual(coverage_gaps(segments, 1.0e4, 1.0e7), [])

    def test_a_wider_sweep_than_demanded_leaves_no_gap(self):
        segments = [
            {"start_hz": 1.0e3, "stop_hz": 1.0e8, "step_hz": 10.0, "dwell_s": 1.0}
        ]
        self.assertEqual(coverage_gaps(segments, 1.0e4, 1.0e7), [])

    def test_inverted_required_range_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_gaps([], 1.0e7, 1.0e4)


class SweepArithmetic(unittest.TestCase):
    def test_widest_step_is_a_share_of_the_bandwidth(self):
        self.assertAlmostEqual(max_allowed_step(1000.0, 0.5), 500.0, places=9)

    def test_step_fraction_outside_the_range_is_rejected(self):
        with self.assertRaises(ValueError):
            max_allowed_step(1000.0, 1.4)

    def test_zero_bandwidth_has_no_allowed_step(self):
        with self.assertRaises(ValueError):
            max_allowed_step(0.0, 0.5)

    def test_step_count_includes_both_end_points(self):
        self.assertEqual(step_count(1000.0, 2000.0, 500.0), 3)

    def test_step_count_truncates_a_partial_last_step(self):
        self.assertEqual(step_count(1000.0, 2200.0, 500.0), 3)

    def test_step_wider_than_the_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            step_count(1000.0, 1200.0, 500.0)

    def test_zero_step_is_rejected(self):
        with self.assertRaises(ValueError):
            step_count(1000.0, 2000.0, 0.0)

    def test_per_point_dwell_divides_the_segment_dwell(self):
        self.assertAlmostEqual(per_step_dwell(4.0, 8), 0.5, places=9)

    def test_per_point_dwell_of_no_point_is_rejected(self):
        with self.assertRaises(ValueError):
            per_step_dwell(4.0, 0)

    def test_fractional_step_count_is_rejected(self):
        with self.assertRaises(ValueError):
            per_step_dwell(4.0, 2.5)

    def test_total_dwell_sums_the_segments(self):
        segments = normalise_verification_run(run())["segments"]
        self.assertAlmostEqual(total_sweep_dwell(segments), 12.3, places=9)

    def test_total_dwell_of_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            total_sweep_dwell([])

    def test_an_accumulated_dwell_a_hair_short_still_meets_the_minimum(self):
        segments = normalise_verification_run(run())["segments"]
        total = total_sweep_dwell(segments)
        self.assertLess(total, 12.3)
        self.assertTrue(meets_minimum_dwell(total, 12.3))

    def test_a_genuinely_short_sweep_does_not_meet_the_minimum(self):
        self.assertFalse(meets_minimum_dwell(8.2, 12.3))

    def test_a_longer_sweep_meets_the_minimum(self):
        self.assertTrue(meets_minimum_dwell(20.0, 12.3))

    def test_negative_minimum_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            meets_minimum_dwell(12.3, -1.0)


class AmbientAndDisposition(unittest.TestCase):
    def test_separation_is_the_limit_less_the_background(self):
        self.assertAlmostEqual(ambient_separation_db(33.0, 27.0), 6.0, places=9)

    def test_a_separation_a_hair_short_is_still_quiet_enough(self):
        self.assertLess(ambient_separation_db(33.3, 27.3), 6.0)
        self.assertTrue(ambient_is_quiet_enough(33.3, 27.3, 6.0))

    def test_a_loud_background_is_not_quiet_enough(self):
        self.assertFalse(ambient_is_quiet_enough(33.3, 31.0, 6.0))

    def test_a_background_above_the_limit_is_not_quiet_enough(self):
        self.assertFalse(ambient_is_quiet_enough(33.3, 40.0, 6.0))

    def test_negative_required_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            ambient_is_quiet_enough(33.3, 27.3, -6.0)

    def test_a_level_clear_of_the_limit_is_compliant(self):
        self.assertEqual(disposition(20.0, 33.3, 2.0), "compliant")

    def test_a_level_whose_upper_bound_lands_on_the_limit_is_compliant(self):
        self.assertGreater(31.1 + 2.2, 33.3)
        self.assertEqual(disposition(31.1, 33.3, 2.2), "compliant")

    def test_a_level_straddling_the_limit_is_inconclusive(self):
        self.assertEqual(disposition(33.0, 33.3, 2.0), "inconclusive")

    def test_a_level_clear_above_the_limit_is_non_compliant(self):
        self.assertEqual(disposition(40.0, 33.3, 2.0), "non-compliant")

    def test_a_perfect_instrument_still_decides_at_the_limit(self):
        self.assertEqual(disposition(33.3, 33.3, 0.0), "compliant")

    def test_negative_uncertainty_in_a_disposition_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition(31.1, 33.3, -2.2)


class RunEvaluation(unittest.TestCase):
    def setUp(self):
        self.index = build_requirement_index([requirement()])

    def test_a_conforming_run_raises_no_finding(self):
        result = evaluate_run(run(), self.index)
        self.assertTrue(result["conformant"])
        self.assertEqual(result["disposition"], "compliant")
        self.assertEqual(result["findings"], [])

    def test_an_unresolved_reference_is_a_finding(self):
        result = evaluate_run(run(reference="CE-99"), self.index)
        self.assertFalse(result["resolved"])
        self.assertFalse(result["conformant"])
        self.assertIn("not in the applicable requirement set", result["findings"][0])

    def test_an_unswept_band_is_a_finding(self):
        record = run()
        record["segments"] = record["segments"][:2]
        result = evaluate_run(record, self.index)
        self.assertFalse(result["conformant"])
        self.assertEqual(len(result["coverage_gaps"]), 1)

    def test_an_oversized_step_is_a_finding(self):
        record = run()
        record["segments"][0]["step_hz"] = 900.0
        result = evaluate_run(record, self.index)
        self.assertFalse(result["conformant"])
        self.assertIn("wider than", result["findings"][0])

    def test_a_short_point_dwell_is_a_finding(self):
        index = build_requirement_index([requirement(min_step_dwell_s=1.0)])
        result = evaluate_run(run(), index)
        self.assertFalse(result["conformant"])
        self.assertIn("per point", result["findings"][0])

    def test_a_short_total_dwell_is_a_finding(self):
        index = build_requirement_index([requirement(min_total_dwell_s=60.0)])
        result = evaluate_run(run(), index)
        self.assertFalse(result["conformant"])
        self.assertIn("in total", " ".join(result["findings"]))

    def test_the_wrong_detector_is_a_finding(self):
        result = evaluate_run(run(detector="average"), self.index)
        self.assertFalse(result["conformant"])
        self.assertIn("detector", " ".join(result["findings"]))

    def test_a_noisy_ambient_is_a_finding(self):
        result = evaluate_run(run(ambient_db=31.0), self.index)
        self.assertFalse(result["conformant"])
        self.assertIn("ambient", " ".join(result["findings"]))

    def test_an_inconclusive_level_is_a_finding(self):
        result = evaluate_run(run(measured_db=33.0, uncertainty_db=2.0), self.index)
        self.assertEqual(result["disposition"], "inconclusive")
        self.assertFalse(result["conformant"])

    def test_a_non_compliant_level_is_a_finding(self):
        result = evaluate_run(run(measured_db=40.0), self.index)
        self.assertEqual(result["disposition"], "non-compliant")
        self.assertFalse(result["conformant"])


class CampaignReview(unittest.TestCase):
    def test_a_clean_campaign_conforms(self):
        review = review_campaign([run()], [requirement()])
        self.assertTrue(review["conformant"])
        self.assertEqual(review["unexercised_requirements"], [])
        self.assertEqual(review["inconclusive_runs"], [])

    def test_a_requirement_nobody_ran_is_a_finding(self):
        review = review_campaign(
            [run()], [requirement(), requirement(id="RE-02", category="radiated-emission")]
        )
        self.assertFalse(review["conformant"])
        self.assertEqual(review["unexercised_requirements"], ["RE-02"])

    def test_an_inconclusive_run_is_listed(self):
        review = review_campaign(
            [run(measured_db=33.0, uncertainty_db=2.0)], [requirement()]
        )
        self.assertEqual(review["inconclusive_runs"], ["RUN-1"])

    def test_findings_are_ordered_by_run_id(self):
        first = run(id="AAA-1", measured_db=40.0)
        second = run(id="ZZZ-9", measured_db=40.0)
        review = review_campaign([second, first], [requirement()])
        self.assertIn("AAA-1", review["findings"][0])
        self.assertIn("ZZZ-9", review["findings"][1])

    def test_duplicate_run_id_is_rejected(self):
        with self.assertRaises(ValueError):
            review_campaign([run(), run()], [requirement()])

    def test_an_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            review_campaign([], [requirement()])

    def test_a_campaign_with_no_requirement_set_is_rejected(self):
        with self.assertRaises(ValueError):
            review_campaign([run()], None)


if __name__ == "__main__":
    unittest.main()
