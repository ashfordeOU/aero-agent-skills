#!/usr/bin/env python3
"""Contract test for the bare-cell contact adherence test purpose (offline).

Walks the clause reasoning step by step: the stressor list that decides
which downstream steps load the contacts, the demand index built from
it, the objectives the check has to demonstrate, the threshold that
decides whether a check is worth running at all, the ordering rule that
separates a post-conditioning pull from an as-built one, the pull load
the service case demands with its margin, the sample that lets the
result speak for the lot, and the verdict that has to stop a plan whose
pull comes before anything weakening. This is the gate 3 review evidence
for the leaf.
"""

import copy
import unittest

from e2008_cell_contact_adherence_test_purpose_logic import (
    ATTACHMENT_STRESSORS,
    CONTACT_ADHERENCE_CHECK_NOT_REQUIRED,
    CONTACT_ADHERENCE_NOT_CONDITIONED,
    CONTACT_ADHERENCE_PLAN_INADEQUATE,
    CONTACT_ADHERENCE_PURPOSE_SERVED,
    DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY,
    PULL_STEP,
    PURPOSE_VERDICTS,
    RECOGNISED_STRESSORS,
    assess_cell_contact_adherence_purpose,
    attachment_demand_index,
    check_is_required,
    conditioning_before_pull,
    demonstration_objectives,
    normalise_stressors,
    pull_capability_adequacy,
    required_pull_load_n,
    sample_coverage,
    validate_contact_adherence_purpose_policy,
)

STRESSORS = [
    "interconnect-welding",
    "coverglass-adhesive-cure",
    "orbital-thermal-cycling",
]

SOUND_SEQUENCE = [
    "incoming-inspection",
    "humidity-soak",
    "thermal-cycling",
    PULL_STEP,
    "visual-inspection",
]

SOUND_CASE = {
    "cell_lot_id": "lot-7",
    "attachment_stressors": list(STRESSORS),
    "planned_sequence": list(SOUND_SEQUENCE),
    "peak_service_load_n": 1.5,
    "planned_pull_load_n": 4.0,
    "samples": 8,
    "lot_size": 200,
}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_contact_adherence_purpose_policy(
                DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY
            ),
            DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_adherence_purpose_policy("default")

    def test_safety_factor_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY)
        broken["required_pull_safety_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_contact_adherence_purpose_policy(broken)

    def test_sample_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY)
        broken["min_sample_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_contact_adherence_purpose_policy(broken)

    def test_zero_min_samples_rejected(self):
        broken = copy.deepcopy(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY)
        broken["min_samples"] = 0
        with self.assertRaises(ValueError):
            validate_contact_adherence_purpose_policy(broken)


class StressorTests(unittest.TestCase):
    def test_known_stressors_are_normalised(self):
        self.assertEqual(
            normalise_stressors([" Interconnect-Welding "]),
            ("interconnect-welding",),
        )

    def test_unknown_stressor_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stressors(["cosmic-ray-shower"])

    def test_repeated_stressor_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stressors(["launch-vibration", "launch-vibration"])

    def test_non_string_stressor_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stressors([7])

    def test_non_sequence_stressors_rejected(self):
        with self.assertRaises(ValueError):
            normalise_stressors("interconnect-welding")

    def test_every_recognised_stressor_carries_an_objective(self):
        self.assertEqual(len(RECOGNISED_STRESSORS), len(ATTACHMENT_STRESSORS))
        for token in RECOGNISED_STRESSORS:
            objective, severity = ATTACHMENT_STRESSORS[token]
            self.assertTrue(objective)
            self.assertGreater(severity, 0.0)


class DemandTests(unittest.TestCase):
    def test_demand_index_adds_the_declared_severities(self):
        expected = sum(ATTACHMENT_STRESSORS[token][1] for token in STRESSORS)
        self.assertAlmostEqual(attachment_demand_index(STRESSORS), expected, places=12)

    def test_empty_stressor_list_gives_no_demand(self):
        self.assertAlmostEqual(attachment_demand_index([]), 0.0, places=12)

    def test_handling_alone_does_not_reach_the_threshold(self):
        index = attachment_demand_index(["panel-integration-handling"])
        self.assertFalse(check_is_required(index))

    def test_welding_alone_reaches_the_threshold(self):
        index = attachment_demand_index(["interconnect-welding"])
        self.assertTrue(check_is_required(index))

    def test_demand_exactly_on_the_threshold_requires_the_check(self):
        index = attachment_demand_index(["interconnect-soldering"])
        self.assertAlmostEqual(
            index,
            float(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY[
                "check_required_demand_index"
            ]),
            places=9,
        )
        self.assertTrue(check_is_required(index))

    def test_objectives_are_one_per_distinct_stressor(self):
        objectives = demonstration_objectives(STRESSORS)
        self.assertEqual(len(objectives), len(STRESSORS))
        self.assertIn("contact-survives-the-weld-schedule", objectives)

    def test_negative_demand_index_rejected(self):
        with self.assertRaises(ValueError):
            check_is_required(-1.0)


class PullLoadTests(unittest.TestCase):
    def test_required_load_is_the_service_peak_times_the_margin(self):
        self.assertAlmostEqual(required_pull_load_n(1.5), 3.0, places=12)

    def test_zero_service_load_rejected(self):
        with self.assertRaises(ValueError):
            required_pull_load_n(0.0)

    def test_capability_above_the_requirement_is_adequate(self):
        result = pull_capability_adequacy(4.0, 3.0)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["shortfall_n"], 0.0, places=12)
        self.assertEqual(result["findings"], [])

    def test_capability_exactly_on_the_requirement_is_adequate(self):
        required = required_pull_load_n(1.5)
        result = pull_capability_adequacy(required, required)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_capability_below_the_requirement_is_named(self):
        result = pull_capability_adequacy(2.0, 3.0)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["shortfall_n"], 1.0, places=9)
        self.assertTrue(any("below the" in note for note in result["findings"]))

    def test_zero_planned_pull_rejected(self):
        with self.assertRaises(ValueError):
            pull_capability_adequacy(0.0, 3.0)


class ConditioningOrderTests(unittest.TestCase):
    def test_conditioning_before_the_pull_is_credited(self):
        result = conditioning_before_pull(SOUND_SEQUENCE)
        self.assertTrue(result["conditioned"])
        self.assertEqual(
            result["conditioning_before_pull"], ("humidity-soak", "thermal-cycling")
        )
        self.assertEqual(result["findings"], [])

    def test_pull_before_any_conditioning_is_as_built(self):
        result = conditioning_before_pull([PULL_STEP, "thermal-cycling"])
        self.assertFalse(result["conditioned"])
        self.assertTrue(any("as-built" in note for note in result["findings"]))

    def test_conditioning_after_the_pull_is_named_not_credited(self):
        result = conditioning_before_pull(
            ["humidity-soak", PULL_STEP, "vacuum-bake"]
        )
        self.assertTrue(result["conditioned"])
        self.assertEqual(result["conditioning_after_pull"], ("vacuum-bake",))
        self.assertTrue(any("after the pull" in note for note in result["findings"]))

    def test_sequence_without_a_pull_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_before_pull(["humidity-soak", "thermal-cycling"])

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_before_pull([PULL_STEP, 3])


class SampleCoverageTests(unittest.TestCase):
    def test_healthy_sample_is_sufficient(self):
        result = sample_coverage(8, 200)
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(result["sample_fraction"], 0.04, places=12)

    def test_fraction_exactly_on_the_floor_is_sufficient(self):
        result = sample_coverage(4, 200)
        self.assertAlmostEqual(
            result["sample_fraction"],
            float(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY["min_sample_fraction"]),
            places=9,
        )
        self.assertTrue(result["sufficient"])

    def test_too_few_samples_fails_even_on_a_tiny_lot(self):
        result = sample_coverage(1, 4)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("below the floor" in note for note in result["findings"]))

    def test_thin_fraction_on_a_large_lot_fails(self):
        result = sample_coverage(3, 5000)
        self.assertFalse(result["sufficient"])
        self.assertTrue(
            any("sample fraction" in note for note in result["findings"])
        )

    def test_more_samples_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_coverage(10, 5)


class AssessmentTests(unittest.TestCase):
    def test_sound_case_serves_the_purpose(self):
        result = assess_cell_contact_adherence_purpose(SOUND_CASE)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_PURPOSE_SERVED)
        self.assertTrue(result["adequate"])
        self.assertTrue(result["conditioned"])
        self.assertEqual(result["findings"], [])

    def test_low_demand_case_needs_no_check(self):
        case = copy.deepcopy(SOUND_CASE)
        case["attachment_stressors"] = ["panel-integration-handling"]
        result = assess_cell_contact_adherence_purpose(case)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_CHECK_NOT_REQUIRED)
        self.assertIsNone(result["adequate"])
        self.assertIsNone(result["required_pull_load_n"])

    def test_unconditioned_pull_stops_the_assessment(self):
        case = copy.deepcopy(SOUND_CASE)
        case["planned_sequence"] = ["incoming-inspection", PULL_STEP]
        result = assess_cell_contact_adherence_purpose(case)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_NOT_CONDITIONED)
        self.assertFalse(result["adequate"])

    def test_weak_bench_makes_the_plan_inadequate(self):
        case = copy.deepcopy(SOUND_CASE)
        case["planned_pull_load_n"] = 1.0
        result = assess_cell_contact_adherence_purpose(case)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_PLAN_INADEQUATE)
        self.assertFalse(result["pull_capability_adequate"])

    def test_thin_sample_makes_the_plan_inadequate(self):
        case = copy.deepcopy(SOUND_CASE)
        case["samples"] = 2
        result = assess_cell_contact_adherence_purpose(case)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_PLAN_INADEQUATE)
        self.assertFalse(result["sample_sufficient"])

    def test_required_load_follows_the_declared_margin(self):
        policy = copy.deepcopy(DEFAULT_CONTACT_ADHERENCE_PURPOSE_POLICY)
        policy["required_pull_safety_factor"] = 3.0
        result = assess_cell_contact_adherence_purpose(SOUND_CASE, policy)
        self.assertAlmostEqual(result["required_pull_load_n"], 4.5, places=12)

    def test_every_verdict_is_reachable(self):
        weak_bench = copy.deepcopy(SOUND_CASE)
        weak_bench["planned_pull_load_n"] = 1.0
        no_conditioning = copy.deepcopy(SOUND_CASE)
        no_conditioning["planned_sequence"] = [PULL_STEP]
        low_demand = copy.deepcopy(SOUND_CASE)
        low_demand["attachment_stressors"] = ["coverglass-adhesive-cure"]
        seen = {
            assess_cell_contact_adherence_purpose(case)["verdict"]
            for case in (SOUND_CASE, weak_bench, no_conditioning, low_demand)
        }
        self.assertEqual(seen, set(PURPOSE_VERDICTS))

    def test_case_without_stressors_rejected(self):
        case = copy.deepcopy(SOUND_CASE)
        del case["attachment_stressors"]
        with self.assertRaises(ValueError):
            assess_cell_contact_adherence_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_contact_adherence_purpose("pull the contacts and see")


if __name__ == "__main__":
    unittest.main()
