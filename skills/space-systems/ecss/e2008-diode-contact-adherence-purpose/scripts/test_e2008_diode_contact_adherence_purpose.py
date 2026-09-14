"""Contract tests for the clause 9.6.6.2.1 diode adherence purpose logic."""

import unittest

from e2008_diode_contact_adherence_purpose_logic import (
    ADHERENCE_JUSTIFIED,
    ADHERENCE_NOT_APPLICABLE,
    COMMON_OBJECTIVE,
    CONTACTS_PRESENT,
    CONTACT_PRESENCE_CATEGORIES,
    DEFAULT_DIODE_ADHERENCE_POLICY,
    DEMAND_BELOW_THRESHOLD,
    DOWNSTREAM_STRESSORS,
    NO_ATTACHED_CONTACTS,
    PULL_LOAD_INSUFFICIENT,
    PURPOSE_VERDICTS,
    RECOGNISED_STRESSORS,
    SAMPLE_COVERAGE_INSUFFICIENT,
    STRESSORS_NOT_DECLARED,
    STRESSOR_WEIGHTS,
    adherence_sample_coverage,
    assess_diode_adherence_purpose,
    attachment_demand_index,
    contact_presence_category,
    required_pull_load_n,
    stressor_evidence_map,
    validate_diode_adherence_policy,
)

ALL_STRESSORS = list(RECOGNISED_STRESSORS)


def _policy(**overrides):
    policy = dict(DEFAULT_DIODE_ADHERENCE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "diode": {"attached_contact_count": 2},
        "stressors": list(ALL_STRESSORS),
        "planned_pull": {"service_peak_load_n": 2.0, "planned_pull_load_n": 4.0},
        "sample": {"devices": 5, "lot_devices": 40},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_adherence_policy(DEFAULT_DIODE_ADHERENCE_POLICY),
            DEFAULT_DIODE_ADHERENCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_adherence_policy("margin")

    def test_a_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_adherence_policy(_policy(pull_load_margin=0.8))

    def test_a_coverage_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_adherence_policy(_policy(min_sample_coverage=1.4))

    def test_a_fractional_minimum_device_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_adherence_policy(_policy(min_sample_devices=3.5))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(PURPOSE_VERDICTS)), 6)

    def test_both_presence_categories_are_declared(self):
        self.assertEqual(len(set(CONTACT_PRESENCE_CATEGORIES)), 2)


class ContactPresenceTests(unittest.TestCase):
    def test_a_device_with_terminals_carries_contacts(self):
        self.assertEqual(
            contact_presence_category({"attached_contact_count": 2}),
            CONTACTS_PRESENT,
        )

    def test_a_device_with_no_terminals_carries_none(self):
        self.assertEqual(
            contact_presence_category({"attached_contact_count": 0}),
            NO_ATTACHED_CONTACTS,
        )

    def test_a_negative_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            contact_presence_category({"attached_contact_count": -1})

    def test_a_missing_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            contact_presence_category({})

    def test_a_non_mapping_device_rejected(self):
        with self.assertRaises(ValueError):
            contact_presence_category(["two"])


class StressorTests(unittest.TestCase):
    def test_the_weights_cover_the_whole_downstream_life(self):
        self.assertAlmostEqual(sum(STRESSOR_WEIGHTS.values()), 1.0, places=9)

    def test_every_stressor_carries_a_weight_and_a_parameter(self):
        self.assertEqual(set(STRESSOR_WEIGHTS), set(DOWNSTREAM_STRESSORS))

    def test_the_full_stressor_set_demands_the_whole_index(self):
        self.assertAlmostEqual(
            attachment_demand_index(ALL_STRESSORS), 1.0, places=9
        )

    def test_a_repeated_stressor_is_counted_once(self):
        once = attachment_demand_index(["orbital-thermal-cycling"])
        twice = attachment_demand_index(
            ["orbital-thermal-cycling", "orbital-thermal-cycling"]
        )
        self.assertAlmostEqual(once, twice, places=12)

    def test_no_stressor_demands_nothing(self):
        self.assertAlmostEqual(attachment_demand_index([]), 0.0, places=12)

    def test_an_unrecognised_stressor_rejected(self):
        with self.assertRaises(ValueError):
            attachment_demand_index(["meteoroid-impact"])

    def test_a_bare_string_is_not_a_stressor_list(self):
        with self.assertRaises(ValueError):
            attachment_demand_index("orbital-thermal-cycling")

    def test_each_stressor_maps_onto_its_evidence_parameter(self):
        mapped = stressor_evidence_map(["launch-random-vibration"])
        self.assertEqual(
            mapped["launch-random-vibration"], "terminal-fatigue-margin"
        )

    def test_the_shared_objective_is_appended_when_any_stressor_is_present(self):
        mapped = stressor_evidence_map(["panel-integration-handling"])
        self.assertIn(COMMON_OBJECTIVE, mapped)

    def test_an_empty_stressor_list_maps_to_nothing(self):
        self.assertEqual(stressor_evidence_map([]), {})

    def test_an_unrecognised_stressor_is_not_mapped_away(self):
        with self.assertRaises(ValueError):
            stressor_evidence_map(["meteoroid-impact"])


class PullLoadAndSampleTests(unittest.TestCase):
    def test_the_required_load_is_the_peak_times_the_margin(self):
        policy = _policy()
        self.assertAlmostEqual(
            required_pull_load_n(2.0, policy),
            2.0 * policy["pull_load_margin"],
            places=9,
        )

    def test_a_larger_service_peak_asks_for_a_larger_pull(self):
        self.assertLess(required_pull_load_n(1.0), required_pull_load_n(4.0))

    def test_a_zero_service_peak_rejected(self):
        with self.assertRaises(ValueError):
            required_pull_load_n(0.0)

    def test_coverage_is_the_sample_over_the_lot(self):
        self.assertAlmostEqual(adherence_sample_coverage(5, 40), 0.125, places=12)

    def test_a_whole_lot_sample_covers_everything(self):
        self.assertAlmostEqual(adherence_sample_coverage(40, 40), 1.0, places=12)

    def test_a_sample_larger_than_its_lot_rejected(self):
        with self.assertRaises(ValueError):
            adherence_sample_coverage(50, 40)

    def test_a_zero_device_sample_rejected(self):
        with self.assertRaises(ValueError):
            adherence_sample_coverage(0, 40)


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_complete_case_justifies_the_verification(self):
        result = assess_diode_adherence_purpose(_case())
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)
        self.assertEqual(result["findings"], [])

    def test_a_device_without_attached_contacts_is_outside_the_check(self):
        result = assess_diode_adherence_purpose(
            _case(diode={"attached_contact_count": 0})
        )
        self.assertEqual(result["verdict"], ADHERENCE_NOT_APPLICABLE)
        self.assertEqual(result["contact_presence"], NO_ATTACHED_CONTACTS)

    def test_an_inapplicable_case_does_not_need_a_pull_plan(self):
        case = _case(diode={"attached_contact_count": 0})
        del case["planned_pull"]
        del case["sample"]
        result = assess_diode_adherence_purpose(case)
        self.assertEqual(result["verdict"], ADHERENCE_NOT_APPLICABLE)

    def test_no_declared_stressor_leaves_the_check_unstated(self):
        result = assess_diode_adherence_purpose(_case(stressors=[]))
        self.assertEqual(result["verdict"], STRESSORS_NOT_DECLARED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_thin_stressor_set_does_not_earn_a_destructive_pull(self):
        result = assess_diode_adherence_purpose(
            _case(stressors=["panel-integration-handling"])
        )
        self.assertEqual(result["verdict"], DEMAND_BELOW_THRESHOLD)

    def test_a_demand_exactly_at_the_floor_is_not_below_it(self):
        policy = _policy(min_demand_index=0.15)
        demand = attachment_demand_index(["panel-integration-handling"])
        self.assertAlmostEqual(demand, policy["min_demand_index"], places=9)
        result = assess_diode_adherence_purpose(
            _case(stressors=["panel-integration-handling"]), policy
        )
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)

    def test_a_pull_below_the_required_load_is_insufficient(self):
        result = assess_diode_adherence_purpose(
            _case(
                planned_pull={
                    "service_peak_load_n": 2.0,
                    "planned_pull_load_n": 2.2,
                }
            )
        )
        self.assertEqual(result["verdict"], PULL_LOAD_INSUFFICIENT)

    def test_a_pull_exactly_at_the_required_load_is_accepted(self):
        policy = _policy()
        required = required_pull_load_n(2.0, policy)
        result = assess_diode_adherence_purpose(
            _case(
                planned_pull={
                    "service_peak_load_n": 2.0,
                    "planned_pull_load_n": required,
                }
            ),
            policy,
        )
        self.assertAlmostEqual(result["planned_pull_load_n"], required, places=9)
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)

    def test_a_thin_sample_cannot_speak_for_the_lot(self):
        result = assess_diode_adherence_purpose(
            _case(sample={"devices": 3, "lot_devices": 400})
        )
        self.assertEqual(result["verdict"], SAMPLE_COVERAGE_INSUFFICIENT)

    def test_too_few_devices_is_a_coverage_deficiency_even_in_a_small_lot(self):
        result = assess_diode_adherence_purpose(
            _case(sample={"devices": 2, "lot_devices": 4})
        )
        self.assertEqual(result["verdict"], SAMPLE_COVERAGE_INSUFFICIENT)

    def test_a_coverage_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_diode_adherence_purpose(
            _case(sample={"devices": 4, "lot_devices": 40}), policy
        )
        self.assertAlmostEqual(
            result["sample_coverage"], policy["min_sample_coverage"], places=9
        )
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)

    def test_demand_outranks_a_thin_sample(self):
        result = assess_diode_adherence_purpose(
            _case(
                stressors=["panel-integration-handling"],
                sample={"devices": 3, "lot_devices": 400},
            )
        )
        self.assertEqual(result["verdict"], DEMAND_BELOW_THRESHOLD)
        self.assertEqual(len(result["findings"]), 2)

    def test_every_finding_is_reported_not_only_the_first(self):
        result = assess_diode_adherence_purpose(
            _case(
                stressors=["panel-integration-handling"],
                planned_pull={
                    "service_peak_load_n": 2.0,
                    "planned_pull_load_n": 1.0,
                },
                sample={"devices": 2, "lot_devices": 400},
            )
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_the_demand_index_is_reported(self):
        result = assess_diode_adherence_purpose(_case())
        self.assertAlmostEqual(result["demand_index"], 1.0, places=9)

    def test_missing_diode_block_rejected(self):
        case = _case()
        del case["diode"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(case)

    def test_missing_stressor_list_rejected(self):
        case = _case()
        del case["stressors"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(case)

    def test_missing_planned_pull_rejected(self):
        case = _case()
        del case["planned_pull"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(case)

    def test_missing_sample_block_rejected(self):
        case = _case()
        del case["sample"]
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(["diode"])

    def test_a_negative_planned_pull_load_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_adherence_purpose(
                _case(
                    planned_pull={
                        "service_peak_load_n": 2.0,
                        "planned_pull_load_n": -4.0,
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
