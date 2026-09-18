#!/usr/bin/env python3
"""Gate 3 contract test for e50-cessation-of-emission.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_cessation_of_emission.py
"""

import unittest

from e50_cessation_of_emission_logic import (
    COMPLIANT,
    DEFAULT_CESSATION_DEADLINE_S,
    NOT_COMMANDABLE,
    ROUTED_THROUGH_EMITTING_CHAIN,
    SINGLE_PATH,
    SOFTWARE_DEPENDENT,
    TOO_SLOW,
    UNAVAILABLE_IN_SAFE_MODE,
    assess_cessation_of_emission,
    credible_response_times,
    meets_deadline,
    path_impairments,
    path_is_credible,
    path_response_time_s,
    response_time_after_single_failure,
    validate_inhibit_path,
)


def path(identifier, latency_s=10.0, through_chain=False, safe_mode=True, software=False):
    return {
        "id": identifier,
        "latency_s": latency_s,
        "routed_through_emitting_chain": through_chain,
        "available_in_safe_mode": safe_mode,
        "requires_onboard_software": software,
    }


class TestPathValidation(unittest.TestCase):
    def test_a_well_formed_path_is_normalized(self):
        record = validate_inhibit_path(path("hpc-off", latency_s=4))
        self.assertEqual(record["id"], "hpc-off")
        self.assertAlmostEqual(record["latency_s"], 4.0, places=9)

    def test_a_missing_key_is_rejected(self):
        broken = path("p1")
        del broken["available_in_safe_mode"]
        with self.assertRaises(ValueError):
            validate_inhibit_path(broken)

    def test_a_non_mapping_path_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_inhibit_path(["hpc-off", 4.0])

    def test_a_negative_latency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_inhibit_path(path("p1", latency_s=-0.5))

    def test_an_integer_standing_in_for_a_flag_is_rejected(self):
        broken = path("p1")
        broken["available_in_safe_mode"] = 1
        with self.assertRaises(ValueError):
            validate_inhibit_path(broken)

    def test_an_empty_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_inhibit_path(path("   "))


class TestImpairments(unittest.TestCase):
    def test_a_clean_path_carries_no_impairment(self):
        self.assertEqual(path_impairments(path("p1")), ())

    def test_a_path_through_the_emitting_chain_is_named(self):
        self.assertIn(
            ROUTED_THROUGH_EMITTING_CHAIN,
            path_impairments(path("p1", through_chain=True)),
        )

    def test_a_path_absent_in_safe_mode_is_named(self):
        self.assertIn(
            UNAVAILABLE_IN_SAFE_MODE, path_impairments(path("p1", safe_mode=False))
        )

    def test_a_software_dependent_path_is_named_but_still_credible(self):
        record = path("p1", software=True)
        self.assertIn(SOFTWARE_DEPENDENT, path_impairments(record))
        self.assertTrue(path_is_credible(record))

    def test_a_path_through_the_emitting_chain_is_not_credible(self):
        self.assertFalse(path_is_credible(path("p1", through_chain=True)))


class TestTiming(unittest.TestCase):
    def test_response_time_sums_reaction_uplink_and_path(self):
        elapsed = path_response_time_s(
            path("p1", latency_s=3.0), uplink_delay_s=1.25, ground_reaction_s=0.75
        )
        self.assertAlmostEqual(elapsed, 5.0, places=9)

    def test_a_budget_landing_on_the_deadline_still_meets_it(self):
        self.assertTrue(meets_deadline(5.0, 5.0))

    def test_a_budget_past_the_deadline_does_not_meet_it(self):
        self.assertFalse(meets_deadline(5.5, 5.0))

    def test_credible_times_exclude_a_discredited_path(self):
        paths = [path("a", 2.0), path("b", 1.0, through_chain=True), path("c", 3.0)]
        times = credible_response_times(paths)
        self.assertEqual(len(times), 2)
        self.assertAlmostEqual(times[0], 2.0, places=9)

    def test_duplicate_path_identifiers_are_rejected(self):
        with self.assertRaises(ValueError):
            credible_response_times([path("a", 2.0), path("a", 3.0)])

    def test_an_empty_path_set_is_rejected(self):
        with self.assertRaises(ValueError):
            credible_response_times([])

    def test_single_failure_time_is_the_second_fastest(self):
        paths = [path("a", 2.0), path("b", 6.0), path("c", 4.0)]
        self.assertAlmostEqual(
            response_time_after_single_failure(paths), 4.0, places=9
        )

    def test_single_failure_time_is_none_with_one_credible_path(self):
        paths = [path("a", 2.0), path("b", 1.0, safe_mode=False)]
        self.assertIsNone(response_time_after_single_failure(paths))


class TestAssessment(unittest.TestCase):
    def test_two_fast_independent_paths_comply(self):
        report = assess_cessation_of_emission([path("a", 5.0), path("b", 9.0)])
        self.assertEqual(report["verdict"], COMPLIANT)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_the_default_deadline_is_carried_into_the_report(self):
        report = assess_cessation_of_emission([path("a", 5.0), path("b", 9.0)])
        self.assertAlmostEqual(
            report["deadline_s"], DEFAULT_CESSATION_DEADLINE_S, places=9
        )

    def test_one_credible_path_is_not_single_failure_tolerant(self):
        report = assess_cessation_of_emission(
            [path("a", 5.0), path("b", 3.0, through_chain=True)]
        )
        self.assertEqual(report["verdict"], SINGLE_PATH)
        self.assertFalse(report["single_failure_tolerant"])

    def test_no_credible_path_is_not_commandable(self):
        report = assess_cessation_of_emission(
            [path("a", 5.0, through_chain=True), path("b", 3.0, safe_mode=False)]
        )
        self.assertEqual(report["verdict"], NOT_COMMANDABLE)
        self.assertIsNone(report["nominal_response_s"])

    def test_a_slow_degraded_path_fails_the_deadline(self):
        report = assess_cessation_of_emission(
            [path("a", 10.0), path("b", 400.0)], deadline_s=120.0
        )
        self.assertEqual(report["verdict"], TOO_SLOW)

    def test_a_degraded_budget_exactly_on_the_deadline_complies(self):
        report = assess_cessation_of_emission(
            [path("a", 10.0), path("b", 100.0)],
            deadline_s=120.0,
            uplink_delay_s=15.0,
            ground_reaction_s=5.0,
        )
        self.assertAlmostEqual(report["degraded_response_s"], 120.0, places=9)
        self.assertEqual(report["verdict"], COMPLIANT)

    def test_a_software_dependent_path_is_a_limitation_not_a_finding(self):
        report = assess_cessation_of_emission(
            [path("a", 5.0, software=True), path("b", 9.0)]
        )
        self.assertEqual(report["verdict"], COMPLIANT)
        self.assertTrue(any(SOFTWARE_DEPENDENT in note for note in report["limitations"]))

    def test_a_negative_deadline_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_cessation_of_emission([path("a", 5.0)], deadline_s=-1.0)


if __name__ == "__main__":
    unittest.main()
