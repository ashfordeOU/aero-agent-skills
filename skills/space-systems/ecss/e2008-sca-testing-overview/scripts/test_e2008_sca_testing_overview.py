#!/usr/bin/env python3
"""Contract test for the solar cell assembly testing overview (offline)."""

import copy
import unittest

from e2008_sca_testing_overview_logic import (
    ACTIVITY_CATEGORY_SHORTFALL,
    ACTIVITY_COVERED,
    ACTIVITY_SAMPLE_SHORTFALL,
    ACTIVITY_SPECIMEN_MISMATCH,
    DEFAULT_SCA_TEST_POLICY,
    PROGRAMME_COMPLETE,
    PROGRAMME_INCOMPLETE,
    REQUIRED_SCA_ACTIVITIES,
    SPECIMEN_KINDS,
    TEST_CATEGORIES,
    assess_sca_test_programme,
    assess_test_activity,
    required_category,
    required_sca_activities,
    resolve_category_coverage,
    sample_size_status,
    specimen_suitability,
    validate_sca_test_policy,
)


def _entry(activity, **overrides):
    category = REQUIRED_SCA_ACTIVITIES[activity]
    entry = {
        "activity": activity,
        "category": category,
        "specimens": list(DEFAULT_SCA_TEST_POLICY["specimen_for_category"][category]),
        "sample_count": DEFAULT_SCA_TEST_POLICY["min_sample_count"][category],
    }
    entry.update(overrides)
    return entry


def _programme(*activities):
    names = activities or tuple(sorted(REQUIRED_SCA_ACTIVITIES))
    return {"activities": [_entry(name) for name in names]}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sca_test_policy(DEFAULT_SCA_TEST_POLICY), DEFAULT_SCA_TEST_POLICY
        )

    def test_policy_covers_every_category(self):
        for category in TEST_CATEGORIES:
            self.assertIn(category, DEFAULT_SCA_TEST_POLICY["specimen_for_category"])
            self.assertIn(category, DEFAULT_SCA_TEST_POLICY["min_sample_count"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sca_test_policy("run everything")

    def test_policy_with_an_out_of_range_share_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        broken["min_qualification_share"] = 1.4
        with self.assertRaises(ValueError):
            validate_sca_test_policy(broken)

    def test_policy_with_an_empty_specimen_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        broken["specimen_for_category"]["acceptance"] = []
        with self.assertRaises(ValueError):
            validate_sca_test_policy(broken)

    def test_policy_with_an_unknown_specimen_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        broken["specimen_for_category"]["acceptance"] = ["engineering-model"]
        with self.assertRaises(ValueError):
            validate_sca_test_policy(broken)

    def test_policy_with_a_zero_sample_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        broken["min_sample_count"]["qualification"] = 0
        with self.assertRaises(ValueError):
            validate_sca_test_policy(broken)


class RequiredSetTests(unittest.TestCase):
    def test_required_set_is_returned_as_a_copy(self):
        first = required_sca_activities()
        first["sca-thermal-cycling"] = "acceptance"
        self.assertEqual(required_sca_activities()["sca-thermal-cycling"], "qualification")

    def test_programme_carries_activities_of_all_three_categories(self):
        categories = set(required_sca_activities().values())
        self.assertEqual(categories, set(TEST_CATEGORIES))

    def test_visual_inspection_serves_both_ends(self):
        self.assertEqual(
            required_category("sca-visual-inspection"), "acceptance-and-qualification"
        )

    def test_thermal_cycling_is_a_qualification_activity(self):
        self.assertEqual(required_category("sca-thermal-cycling"), "qualification")

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            required_category("sca-vibration-survey")


class CategoryCoverageTests(unittest.TestCase):
    def test_matching_category_covers_the_obligation(self):
        result = resolve_category_coverage("sca-thermal-cycling", "qualification")
        self.assertTrue(result["covers_required"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_half_of_a_combined_obligation_is_a_shortfall(self):
        result = resolve_category_coverage("sca-visual-inspection", "acceptance")
        self.assertFalse(result["covers_required"])
        self.assertEqual(result["uncovered_obligations"], ["qualification"])
        self.assertTrue(any("uncovered" in f for f in result["findings"]))

    def test_the_other_half_of_a_combined_obligation_is_also_a_shortfall(self):
        result = resolve_category_coverage("sca-adherence-measurement", "qualification")
        self.assertEqual(result["uncovered_obligations"], ["acceptance"])

    def test_an_acceptance_activity_run_as_qualification_only_is_a_shortfall(self):
        result = resolve_category_coverage("sca-dimensional-measurement", "qualification")
        self.assertFalse(result["covers_required"])
        self.assertEqual(result["uncovered_obligations"], ["acceptance"])

    def test_doing_more_than_is_owed_is_accepted_by_default(self):
        result = resolve_category_coverage(
            "sca-dimensional-measurement", "acceptance-and-qualification"
        )
        self.assertTrue(result["covers_required"])
        self.assertEqual(result["additional_obligations"], ["qualification"])
        self.assertTrue(result["accepted"])

    def test_a_strict_policy_refuses_a_category_above_the_requirement(self):
        policy = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        policy["allow_category_above_requirement"] = False
        result = resolve_category_coverage(
            "sca-dimensional-measurement", "acceptance-and-qualification", policy
        )
        self.assertTrue(result["covers_required"])
        self.assertFalse(result["accepted"])

    def test_unknown_declared_category_rejected(self):
        with self.assertRaises(ValueError):
            resolve_category_coverage("sca-thermal-cycling", "screening")


class SpecimenTests(unittest.TestCase):
    def test_qualification_activity_runs_on_a_coupon(self):
        result = specimen_suitability("qualification", ["qualification-coupon"])
        self.assertTrue(result["suitable"])
        self.assertEqual(result["findings"], [])

    def test_acceptance_activity_runs_on_a_flight_lot_sample(self):
        result = specimen_suitability("acceptance", ["flight-lot-sample"])
        self.assertTrue(result["suitable"])

    def test_combined_activity_needs_both_articles(self):
        result = specimen_suitability(
            "acceptance-and-qualification", ["qualification-coupon"]
        )
        self.assertFalse(result["suitable"])
        self.assertEqual(result["missing_specimens"], ["flight-lot-sample"])

    def test_acceptance_activity_on_a_coupon_only_is_unsuitable(self):
        result = specimen_suitability("acceptance", ["qualification-coupon"])
        self.assertFalse(result["suitable"])
        self.assertEqual(result["missing_specimens"], ["flight-lot-sample"])

    def test_surplus_article_is_reported_but_still_suitable(self):
        result = specimen_suitability(
            "acceptance", ["flight-lot-sample", "qualification-coupon"]
        )
        self.assertTrue(result["suitable"])
        self.assertEqual(result["surplus_specimens"], ["qualification-coupon"])
        self.assertTrue(any("does not owe" in f for f in result["findings"]))

    def test_every_specimen_kind_is_a_declared_article(self):
        self.assertEqual(len(SPECIMEN_KINDS), 2)
        for kind in SPECIMEN_KINDS:
            self.assertTrue(specimen_suitability("acceptance-and-qualification", list(SPECIMEN_KINDS))["suitable"])
            self.assertIn(kind, SPECIMEN_KINDS)

    def test_empty_specimen_list_rejected(self):
        with self.assertRaises(ValueError):
            specimen_suitability("acceptance", [])

    def test_repeated_specimen_rejected(self):
        with self.assertRaises(ValueError):
            specimen_suitability("acceptance", ["flight-lot-sample", "flight-lot-sample"])

    def test_unknown_specimen_rejected(self):
        with self.assertRaises(ValueError):
            specimen_suitability("acceptance", ["engineering-model"])


class SampleSizeTests(unittest.TestCase):
    def test_sample_at_the_minimum_is_sufficient(self):
        result = sample_size_status("qualification", 5)
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["required_count"], 5)

    def test_sample_below_the_minimum_is_short(self):
        result = sample_size_status("qualification", 3)
        self.assertFalse(result["sufficient"])
        self.assertTrue(any("against a required" in f for f in result["findings"]))

    def test_acceptance_minimum_is_lower_than_qualification(self):
        self.assertTrue(sample_size_status("acceptance", 3)["sufficient"])
        self.assertFalse(sample_size_status("qualification", 3)["sufficient"])

    def test_zero_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sample_size_status("acceptance", 0)

    def test_fractional_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sample_size_status("acceptance", 3.5)

    def test_a_stricter_policy_can_fail_a_nominal_sample(self):
        policy = copy.deepcopy(DEFAULT_SCA_TEST_POLICY)
        policy["min_sample_count"]["acceptance"] = 8
        self.assertFalse(sample_size_status("acceptance", 3, policy)["sufficient"])


class ActivityTests(unittest.TestCase):
    def test_well_formed_activity_is_covered(self):
        record = assess_test_activity(_entry("sca-thermal-cycling"))
        self.assertEqual(record["verdict"], ACTIVITY_COVERED)
        self.assertEqual(record["findings"], [])
        self.assertTrue(record["carries_qualification"])

    def test_acceptance_activity_does_not_carry_qualification(self):
        record = assess_test_activity(_entry("sca-dimensional-measurement"))
        self.assertEqual(record["verdict"], ACTIVITY_COVERED)
        self.assertFalse(record["carries_qualification"])

    def test_combined_activity_carries_qualification(self):
        record = assess_test_activity(_entry("sca-visual-inspection"))
        self.assertTrue(record["carries_qualification"])
        self.assertEqual(record["verdict"], ACTIVITY_COVERED)

    def test_category_shortfall_outranks_the_other_arms(self):
        record = assess_test_activity(
            _entry(
                "sca-visual-inspection",
                category="acceptance",
                specimens=["flight-lot-sample"],
                sample_count=1,
            )
        )
        self.assertEqual(record["verdict"], ACTIVITY_CATEGORY_SHORTFALL)

    def test_wrong_article_is_a_specimen_mismatch(self):
        record = assess_test_activity(
            _entry("sca-thermal-cycling", specimens=["flight-lot-sample"])
        )
        self.assertEqual(record["verdict"], ACTIVITY_SPECIMEN_MISMATCH)
        self.assertEqual(
            record["specimens"]["missing_specimens"], ["qualification-coupon"]
        )

    def test_thin_sample_is_a_sample_shortfall(self):
        record = assess_test_activity(_entry("sca-humidity-exposure", sample_count=2))
        self.assertEqual(record["verdict"], ACTIVITY_SAMPLE_SHORTFALL)
        self.assertFalse(record["samples"]["sufficient"])

    def test_activity_without_specimens_rejected(self):
        entry = _entry("sca-thermal-cycling")
        del entry["specimens"]
        with self.assertRaises(ValueError):
            assess_test_activity(entry)

    def test_activity_with_an_unknown_name_rejected(self):
        entry = _entry("sca-thermal-cycling")
        entry["activity"] = "sca-bake-out"
        with self.assertRaises(ValueError):
            assess_test_activity(entry)

    def test_non_mapping_activity_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_activity("sca-thermal-cycling")


class ProgrammeTests(unittest.TestCase):
    def test_full_programme_is_complete(self):
        result = assess_sca_test_programme(_programme())
        self.assertEqual(result["verdict"], PROGRAMME_COMPLETE)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertEqual(result["open_activities"], [])
        self.assertEqual(result["findings"], [])

    def test_full_programme_is_mostly_qualification_bearing(self):
        result = assess_sca_test_programme(_programme())
        self.assertAlmostEqual(result["qualification_share"], 6.0 / 7.0, places=9)
        self.assertTrue(result["combined_campaign"])

    def test_absent_activity_opens_the_programme(self):
        names = [a for a in sorted(REQUIRED_SCA_ACTIVITIES) if a != "sca-humidity-exposure"]
        result = assess_sca_test_programme(_programme(*names))
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)
        self.assertEqual(result["absent_activities"], ["sca-humidity-exposure"])
        self.assertAlmostEqual(result["coverage_fraction"], 6.0 / 7.0, places=9)

    def test_share_exactly_on_the_required_limit_still_reads_as_combined(self):
        result = assess_sca_test_programme(
            _programme("sca-dimensional-measurement", "sca-thermal-cycling")
        )
        self.assertAlmostEqual(result["qualification_share"], 0.50, places=9)
        self.assertAlmostEqual(result["required_qualification_share"], 0.50, places=9)
        self.assertTrue(result["combined_campaign"])

    def test_acceptance_only_programme_is_not_a_combined_campaign(self):
        result = assess_sca_test_programme(_programme("sca-dimensional-measurement"))
        self.assertAlmostEqual(result["qualification_share"], 0.0, places=9)
        self.assertFalse(result["combined_campaign"])
        self.assertTrue(any("falls below" in f for f in result["findings"]))

    def test_programme_groups_activities_by_verdict(self):
        case = _programme()
        case["activities"][0] = _entry(
            case["activities"][0]["activity"], sample_count=1
        )
        grouped = assess_sca_test_programme(case)["grouped_by_verdict"]
        self.assertEqual(len(grouped[ACTIVITY_SAMPLE_SHORTFALL]), 1)
        self.assertEqual(len(grouped[ACTIVITY_COVERED]), 6)

    def test_programme_collects_every_finding(self):
        case = _programme()
        case["activities"][-1] = _entry(
            case["activities"][-1]["activity"], specimens=["flight-lot-sample"]
        )
        findings = assess_sca_test_programme(case)["findings"]
        self.assertTrue(any("none is declared" in f for f in findings))

    def test_repeated_activity_rejected(self):
        case = {
            "activities": [
                _entry("sca-thermal-cycling"),
                _entry("sca-thermal-cycling"),
            ]
        }
        with self.assertRaises(ValueError):
            assess_sca_test_programme(case)

    def test_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_test_programme({"activities": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_test_programme([_entry("sca-thermal-cycling")])


if __name__ == "__main__":
    unittest.main()
