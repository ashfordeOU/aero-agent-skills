#!/usr/bin/env python3
"""Contract test for the photovoltaic assembly process validation (offline).

Walks the clause workflow step by step: the configuration signature, the
coverage test including the validated numeric range, the run
admissibility and process-change supersession checks, the
outstanding-run plan, and the release gate that has to stop production
while any configuration is open. This is the gate 3 review evidence for
the leaf.
"""

import copy
import unittest

from e2008_pva_process_validation_logic import (
    CURRENT,
    DEFAULT_PROCESS_POLICY,
    EXPIRED_BY_AGE,
    GOVERNING_ATTRIBUTES,
    PRODUCTION_RELEASE_PERMITTED,
    PRODUCTION_RELEASE_WITHHELD,
    SUPERSEDED_BY_PROCESS_CHANGE,
    assess_configuration,
    assess_production_readiness,
    configuration_signature,
    plan_validation_runs,
    run_covers_configuration,
    run_is_admissible,
    validate_process_policy,
    validation_currency,
)

CFG_FIELD = {
    "id": "cfg-field",
    "cell-assembly-type": "triple-junction-cic",
    "interconnect-design": "silver-mesh-three-tab",
    "substrate-construction": "aluminium-honeycomb-cfrp",
    "bonding-adhesive": "space-grade-silicone-a",
    "layout-edge-condition": "field-string",
    "coverglass-thickness-um": 100.0,
}

CFG_EDGE = dict(CFG_FIELD, id="cfg-edge", **{"layout-edge-condition": "edge-string"})

CFG_YOKE = dict(
    CFG_FIELD,
    id="cfg-yoke",
    **{"substrate-construction": "cfrp-solid-laminate"}
)

RUN_FIELD = {
    "id": "run-field",
    "cell-assembly-type": "triple-junction-cic",
    "interconnect-design": "silver-mesh-three-tab",
    "substrate-construction": "aluminium-honeycomb-cfrp",
    "bonding-adhesive": "space-grade-silicone-a",
    "layout-edge-condition": "field-string",
    "coverglass-thickness-um": {"min": 80.0, "max": 150.0},
    "age_days": 120,
    "process_change_index": 2,
    "coupon_count": 5,
    "outcome": "passed",
}

RUN_EDGE = dict(RUN_FIELD, id="run-edge", **{"layout-edge-condition": "edge-string"})

SOUND_CAMPAIGN = {
    "configurations": [copy.deepcopy(CFG_FIELD), copy.deepcopy(CFG_EDGE)],
    "validation_runs": [copy.deepcopy(RUN_FIELD), copy.deepcopy(RUN_EDGE)],
    "process_change_index": 2,
}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_process_policy(DEFAULT_PROCESS_POLICY), DEFAULT_PROCESS_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_policy("default")

    def test_zero_validity_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_PROCESS_POLICY)
        broken["max_validity_days"] = 0
        with self.assertRaises(ValueError):
            validate_process_policy(broken)

    def test_zero_coupon_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_PROCESS_POLICY)
        broken["min_validation_coupons"] = 0
        with self.assertRaises(ValueError):
            validate_process_policy(broken)

    def test_non_boolean_currency_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_PROCESS_POLICY)
        broken["require_current_validation"] = "yes"
        with self.assertRaises(ValueError):
            validate_process_policy(broken)


class SignatureTests(unittest.TestCase):
    def test_identical_configurations_share_a_signature(self):
        other = copy.deepcopy(CFG_FIELD)
        other["id"] = "cfg-field-copy"
        self.assertEqual(
            configuration_signature(CFG_FIELD), configuration_signature(other)
        )

    def test_a_different_layout_condition_changes_the_signature(self):
        self.assertNotEqual(
            configuration_signature(CFG_FIELD), configuration_signature(CFG_EDGE)
        )

    def test_a_different_coverglass_thickness_changes_the_signature(self):
        thicker = copy.deepcopy(CFG_FIELD)
        thicker["coverglass-thickness-um"] = 150.0
        self.assertNotEqual(
            configuration_signature(CFG_FIELD), configuration_signature(thicker)
        )

    def test_every_governing_attribute_is_required(self):
        for attribute in GOVERNING_ATTRIBUTES:
            partial = copy.deepcopy(CFG_FIELD)
            del partial[attribute]
            with self.assertRaises(ValueError):
                configuration_signature(partial)

    def test_non_positive_coverglass_thickness_rejected(self):
        broken = copy.deepcopy(CFG_FIELD)
        broken["coverglass-thickness-um"] = 0.0
        with self.assertRaises(ValueError):
            configuration_signature(broken)

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            configuration_signature("the standard panel")


class CoverageTests(unittest.TestCase):
    def test_a_matching_run_covers_the_configuration(self):
        result = run_covers_configuration(RUN_FIELD, CFG_FIELD)
        self.assertTrue(result["covers"])
        self.assertEqual(result["mismatched_attributes"], [])

    def test_a_different_layout_condition_is_not_covered(self):
        result = run_covers_configuration(RUN_FIELD, CFG_EDGE)
        self.assertFalse(result["covers"])
        self.assertEqual(result["mismatched_attributes"], ["layout-edge-condition"])

    def test_a_different_substrate_is_not_covered(self):
        result = run_covers_configuration(RUN_FIELD, CFG_YOKE)
        self.assertFalse(result["covers"])
        self.assertEqual(result["mismatched_attributes"], ["substrate-construction"])

    def test_a_thickness_outside_the_validated_range_is_not_covered(self):
        configuration = copy.deepcopy(CFG_FIELD)
        configuration["coverglass-thickness-um"] = 300.0
        result = run_covers_configuration(RUN_FIELD, configuration)
        self.assertFalse(result["covers"])
        self.assertEqual(result["mismatched_attributes"], ["coverglass-thickness-um"])

    def test_a_thickness_on_the_edge_of_the_range_is_covered(self):
        # 0.15 mm converted to micrometre does not land on 150.0 bit for bit.
        configuration = copy.deepcopy(CFG_FIELD)
        configuration["coverglass-thickness-um"] = 0.15 * 1000.0
        self.assertAlmostEqual(
            configuration["coverglass-thickness-um"], 150.0, places=9
        )
        self.assertTrue(run_covers_configuration(RUN_FIELD, configuration)["covers"])

    def test_the_mismatch_is_named_in_the_findings(self):
        result = run_covers_configuration(RUN_FIELD, CFG_EDGE)
        self.assertTrue(
            any("layout-edge-condition" in note for note in result["findings"])
        )

    def test_a_run_without_a_validated_range_rejected(self):
        run = copy.deepcopy(RUN_FIELD)
        run["coverglass-thickness-um"] = 100.0
        with self.assertRaises(ValueError):
            run_covers_configuration(run, CFG_FIELD)

    def test_an_inverted_validated_range_rejected(self):
        run = copy.deepcopy(RUN_FIELD)
        run["coverglass-thickness-um"] = {"min": 150.0, "max": 80.0}
        with self.assertRaises(ValueError):
            run_covers_configuration(run, CFG_FIELD)

    def test_a_run_missing_a_governing_attribute_rejected(self):
        run = copy.deepcopy(RUN_FIELD)
        del run["bonding-adhesive"]
        with self.assertRaises(ValueError):
            run_covers_configuration(run, CFG_FIELD)


class CurrencyTests(unittest.TestCase):
    def test_a_recent_run_at_the_current_index_is_current(self):
        result = validation_currency(RUN_FIELD, 2)
        self.assertEqual(result["status"], CURRENT)
        self.assertTrue(result["current"])

    def test_a_run_past_its_validity_window_has_expired(self):
        run = copy.deepcopy(RUN_FIELD)
        run["age_days"] = 400
        result = validation_currency(run, 2)
        self.assertEqual(result["status"], EXPIRED_BY_AGE)
        self.assertFalse(result["current"])

    def test_a_run_exactly_on_the_validity_window_is_still_current(self):
        run = copy.deepcopy(RUN_FIELD)
        run["age_days"] = int(DEFAULT_PROCESS_POLICY["max_validity_days"])
        self.assertEqual(validation_currency(run, 2)["status"], CURRENT)

    def test_a_process_change_supersedes_an_older_run(self):
        result = validation_currency(RUN_FIELD, 3)
        self.assertEqual(result["status"], SUPERSEDED_BY_PROCESS_CHANGE)
        self.assertTrue(any("process change" in note for note in result["findings"]))

    def test_a_run_ahead_of_the_current_index_rejected(self):
        with self.assertRaises(ValueError):
            validation_currency(RUN_FIELD, 1)

    def test_a_negative_age_rejected(self):
        run = copy.deepcopy(RUN_FIELD)
        run["age_days"] = -5
        with self.assertRaises(ValueError):
            validation_currency(run, 2)


class AdmissibilityTests(unittest.TestCase):
    def test_a_passed_current_run_with_enough_coupons_is_admissible(self):
        result = run_is_admissible(RUN_FIELD, 2)
        self.assertTrue(result["admissible"])
        self.assertEqual(result["currency"], CURRENT)

    def test_a_failed_run_validates_nothing(self):
        run = copy.deepcopy(RUN_FIELD)
        run["outcome"] = "failed"
        result = run_is_admissible(run, 2)
        self.assertFalse(result["admissible"])
        self.assertTrue(any("did not pass" in note for note in result["findings"]))

    def test_too_few_coupons_makes_a_run_inadmissible(self):
        run = copy.deepcopy(RUN_FIELD)
        run["coupon_count"] = 1
        result = run_is_admissible(run, 2)
        self.assertFalse(result["admissible"])

    def test_a_superseded_run_is_inadmissible(self):
        self.assertFalse(run_is_admissible(RUN_FIELD, 4)["admissible"])

    def test_waiving_currency_readmits_an_aged_run(self):
        policy = copy.deepcopy(DEFAULT_PROCESS_POLICY)
        policy["require_current_validation"] = False
        run = copy.deepcopy(RUN_FIELD)
        run["age_days"] = 900
        result = run_is_admissible(run, 2, policy)
        self.assertTrue(result["admissible"])
        self.assertEqual(result["currency"], EXPIRED_BY_AGE)

    def test_an_unknown_outcome_rejected(self):
        run = copy.deepcopy(RUN_FIELD)
        run["outcome"] = "mostly-fine"
        with self.assertRaises(ValueError):
            run_is_admissible(run, 2)


class ConfigurationAssessmentTests(unittest.TestCase):
    def test_a_covered_configuration_names_its_run(self):
        result = assess_configuration(CFG_FIELD, [RUN_FIELD, RUN_EDGE], 2)
        self.assertTrue(result["validated"])
        self.assertEqual(result["validating_run_id"], "run-field")

    def test_an_uncovered_configuration_says_no_run_was_carried_out(self):
        result = assess_configuration(CFG_YOKE, [RUN_FIELD, RUN_EDGE], 2)
        self.assertFalse(result["validated"])
        self.assertIn("no validation run", result["reason"])

    def test_a_matching_but_inadmissible_run_is_named(self):
        run = copy.deepcopy(RUN_FIELD)
        run["coupon_count"] = 1
        result = assess_configuration(CFG_FIELD, [run], 2)
        self.assertFalse(result["validated"])
        self.assertIn("not admissible", result["reason"])

    def test_an_admissible_run_wins_over_an_inadmissible_one(self):
        stale = copy.deepcopy(RUN_FIELD)
        stale["id"] = "run-stale"
        stale["outcome"] = "failed"
        result = assess_configuration(CFG_FIELD, [stale, RUN_FIELD], 2)
        self.assertTrue(result["validated"])
        self.assertEqual(result["validating_run_id"], "run-field")

    def test_a_non_sequence_run_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_configuration(CFG_FIELD, RUN_FIELD, 2)


class PlanTests(unittest.TestCase):
    def test_configurations_sharing_a_signature_need_one_run(self):
        twin = copy.deepcopy(CFG_FIELD)
        twin["id"] = "cfg-field-twin"
        plan = plan_validation_runs([CFG_FIELD, twin])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["configuration_ids"], ["cfg-field", "cfg-field-twin"])

    def test_distinct_signatures_need_a_run_each(self):
        plan = plan_validation_runs([CFG_FIELD, CFG_EDGE, CFG_YOKE])
        self.assertEqual(len(plan), 3)

    def test_the_plan_carries_the_governing_attributes(self):
        plan = plan_validation_runs([CFG_EDGE])
        self.assertEqual(
            plan[0]["governing_attributes"]["layout-edge-condition"], "edge-string"
        )

    def test_nothing_open_needs_no_run(self):
        self.assertEqual(plan_validation_runs([]), [])

    def test_a_non_sequence_configuration_list_rejected(self):
        with self.assertRaises(ValueError):
            plan_validation_runs(CFG_FIELD)


class ReadinessTests(unittest.TestCase):
    def test_full_coverage_permits_production_release(self):
        result = assess_production_readiness(SOUND_CAMPAIGN)
        self.assertEqual(result["verdict"], PRODUCTION_RELEASE_PERMITTED)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=12)
        self.assertEqual(result["outstanding_runs"], [])

    def test_an_unvalidated_configuration_withholds_release(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["configurations"].append(copy.deepcopy(CFG_YOKE))
        result = assess_production_readiness(campaign)
        self.assertEqual(result["verdict"], PRODUCTION_RELEASE_WITHHELD)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["outstanding_runs"]), 1)

    def test_partial_coverage_is_reported_as_a_fraction(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["configurations"].append(copy.deepcopy(CFG_YOKE))
        result = assess_production_readiness(campaign)
        self.assertEqual(result["validated_count"], 2)
        self.assertEqual(result["configuration_count"], 3)
        self.assertAlmostEqual(result["coverage_fraction"], 2.0 / 3.0, places=12)

    def test_a_process_change_withdraws_every_earlier_run(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["process_change_index"] = 3
        result = assess_production_readiness(campaign)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.0, places=12)
        self.assertEqual(len(result["outstanding_runs"]), 2)

    def test_two_open_configurations_with_one_signature_need_one_run(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        twin = copy.deepcopy(CFG_YOKE)
        twin["id"] = "cfg-yoke-twin"
        campaign["configurations"].extend([copy.deepcopy(CFG_YOKE), twin])
        result = assess_production_readiness(campaign)
        self.assertEqual(len(result["outstanding_runs"]), 1)
        self.assertEqual(
            result["outstanding_runs"][0]["configuration_ids"],
            ["cfg-yoke", "cfg-yoke-twin"],
        )

    def test_no_runs_at_all_withholds_release(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["validation_runs"] = []
        result = assess_production_readiness(campaign)
        self.assertEqual(result["verdict"], PRODUCTION_RELEASE_WITHHELD)
        self.assertEqual(result["validated_count"], 0)

    def test_a_repeated_configuration_id_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["configurations"].append(copy.deepcopy(CFG_FIELD))
        with self.assertRaises(ValueError):
            assess_production_readiness(campaign)

    def test_an_empty_configuration_set_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["configurations"] = []
        with self.assertRaises(ValueError):
            assess_production_readiness(campaign)

    def test_a_missing_run_sequence_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        del campaign["validation_runs"]
        with self.assertRaises(ValueError):
            assess_production_readiness(campaign)

    def test_a_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_readiness("everything is validated")


if __name__ == "__main__":
    unittest.main()
