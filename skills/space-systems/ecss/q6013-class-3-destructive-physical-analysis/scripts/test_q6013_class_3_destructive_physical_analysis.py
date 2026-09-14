"""Contract tests for the clause 6.3.9 class 3 destructive sampling logic.

The cases follow the assessment one step at a time: the trigger register that
decides whether a teardown is owed at all, the recorded reason a waived lot
still needs, the integer sample plan and the lot too small to survive it, the
conditions a prior analysis has to meet before it is credited, the grouping of
observations against the defect register, and the verdicts a lot can end in.
Limits are exercised on both sides and exactly on the boundary.
"""

import unittest

from q6013_class_3_destructive_physical_analysis_logic import (
    DEFAULT_CREDIT_AGE_LIMIT_MONTHS,
    DEFECT_REGISTER,
    TRIGGER_REGISTER,
    assess_class3_destructive_analysis,
    categorize_findings,
    fired_triggers,
    prior_analysis_credit,
    teardown_sample_size,
    waiver_status,
)

NO_TRIGGERS = {item: False for item in TRIGGER_REGISTER}


def _triggers(**overrides):
    conditions = dict(NO_TRIGGERS)
    conditions.update(overrides)
    return conditions


def _record(**overrides):
    record = {
        "manufacturer_matches": True,
        "technology_matches": True,
        "date_code_matches": True,
        "months_since": 6.0,
        "major_defects_found": 0,
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "lot_size": 500,
        "trigger_conditions": _triggers(**{"unfranchised-source": True}),
        "observations": [],
    }
    spec.update(overrides)
    return spec


class TriggerRegisterTests(unittest.TestCase):
    def test_quiet_lot_fires_nothing(self):
        self.assertEqual(fired_triggers(NO_TRIGGERS), [])

    def test_single_condition_fires_its_trigger(self):
        self.assertEqual(
            fired_triggers(_triggers(**{"unfranchised-source": True})),
            ["unfranchised-source"],
        )

    def test_several_conditions_all_reported_in_register_order(self):
        result = fired_triggers(
            _triggers(
                **{"technology-on-watch-register": True, "unfranchised-source": True}
            )
        )
        self.assertEqual(result, ["unfranchised-source", "technology-on-watch-register"])

    def test_omitted_condition_has_not_fired(self):
        conditions = dict(NO_TRIGGERS)
        del conditions["date-code-beyond-shelf-limit"]
        self.assertEqual(fired_triggers(conditions), [])

    def test_unknown_trigger_rejected(self):
        conditions = dict(NO_TRIGGERS)
        conditions["procurement-felt-uneasy"] = True
        with self.assertRaises(ValueError):
            fired_triggers(conditions)

    def test_non_boolean_condition_rejected(self):
        conditions = dict(NO_TRIGGERS)
        conditions["unfranchised-source"] = "probably"
        with self.assertRaises(ValueError):
            fired_triggers(conditions)


class WaiverTests(unittest.TestCase):
    def test_quiet_lot_with_a_written_reason_is_waived(self):
        result = waiver_status([], "franchised distributor, flown technology, two prior lots")
        self.assertFalse(result["sampling_required"])
        self.assertTrue(result["justification_recorded"])

    def test_quiet_lot_without_a_reason_is_not_waived(self):
        self.assertFalse(waiver_status([], None)["justification_recorded"])

    def test_blank_reason_does_not_count_as_recorded(self):
        self.assertFalse(waiver_status([], "   ")["justification_recorded"])

    def test_fired_lot_cannot_be_waived_by_a_reason(self):
        result = waiver_status(["unfranchised-source"], "we are in a hurry")
        self.assertTrue(result["sampling_required"])
        self.assertFalse(result["justification_recorded"])

    def test_non_sequence_triggers_rejected(self):
        with self.assertRaises(ValueError):
            waiver_status("unfranchised-source")


class SampleSizeTests(unittest.TestCase):
    def test_proportional_sample_for_a_round_lot(self):
        self.assertEqual(teardown_sample_size(500), 5)

    def test_proportional_sample_rounds_up(self):
        self.assertEqual(teardown_sample_size(501), 6)

    def test_small_lot_raised_to_the_floor(self):
        self.assertEqual(teardown_sample_size(40), 2)

    def test_large_lot_limited_by_the_cap(self):
        self.assertEqual(teardown_sample_size(100000), 10)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(teardown_sample_size(1), 1)

    def test_sample_is_reproducible_for_the_same_lot(self):
        self.assertEqual(teardown_sample_size(637), teardown_sample_size(637))

    def test_cap_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(500, floor=8, cap=4)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(0)


class PriorAnalysisCreditTests(unittest.TestCase):
    def test_matching_recent_clean_analysis_is_credited(self):
        result = prior_analysis_credit(_record())
        self.assertTrue(result["credited"])
        self.assertEqual(result["reasons"], [])

    def test_analysis_exactly_on_the_age_limit_is_still_credited(self):
        result = prior_analysis_credit(_record(months_since=DEFAULT_CREDIT_AGE_LIMIT_MONTHS))
        self.assertAlmostEqual(result["months_remaining"], 0.0, places=9)
        self.assertTrue(result["credited"])

    def test_analysis_past_the_age_limit_is_not_credited(self):
        self.assertFalse(prior_analysis_credit(_record(months_since=40.0))["credited"])

    def test_different_manufacturer_is_not_credited(self):
        self.assertFalse(prior_analysis_credit(_record(manufacturer_matches=False))["credited"])

    def test_different_date_code_is_not_credited(self):
        self.assertFalse(prior_analysis_credit(_record(date_code_matches=False))["credited"])

    def test_prior_major_defect_is_not_credited(self):
        self.assertFalse(prior_analysis_credit(_record(major_defects_found=1))["credited"])

    def test_every_refusal_reason_is_named_not_just_the_first(self):
        result = prior_analysis_credit(
            _record(manufacturer_matches=False, technology_matches=False, months_since=40.0)
        )
        self.assertGreaterEqual(len(result["reasons"]), 3)

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["months_since"]
        with self.assertRaises(ValueError):
            prior_analysis_credit(record)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            prior_analysis_credit(_record(months_since=-1.0))


class FindingGroupingTests(unittest.TestCase):
    def test_no_observation_groups_to_nothing(self):
        result = categorize_findings([])
        self.assertEqual(result["major"], [])
        self.assertEqual(result["total"], 0)

    def test_major_observation_grouped_as_major(self):
        self.assertEqual(categorize_findings(["die-crack"])["major"], ["die-crack"])

    def test_minor_observation_grouped_as_minor(self):
        self.assertEqual(categorize_findings(["marking-smear"])["minor"], ["marking-smear"])

    def test_mixed_observations_grouped_separately(self):
        result = categorize_findings(["wire-bond-lift", "lead-frame-burr"])
        self.assertEqual(len(result["major"]), 1)
        self.assertEqual(len(result["minor"]), 1)

    def test_every_registered_code_is_grouped(self):
        result = categorize_findings(list(DEFECT_REGISTER))
        self.assertEqual(result["total"], len(DEFECT_REGISTER))

    def test_unregistered_observation_rejected(self):
        with self.assertRaises(ValueError):
            categorize_findings(["looked-a-bit-odd"])

    def test_register_severity_outside_the_two_values_rejected(self):
        with self.assertRaises(ValueError):
            categorize_findings(["die-crack"], register={"die-crack": "cosmetic"})


class AssessmentTests(unittest.TestCase):
    def test_quiet_lot_with_a_recorded_reason_owes_no_teardown(self):
        result = assess_class3_destructive_analysis(
            _spec(
                trigger_conditions=_triggers(),
                waiver_justification="franchised source, flown technology, prior lots clean",
            )
        )
        self.assertEqual(result["verdict"], "destructive-sampling-not-required")
        self.assertTrue(result["accepted"])

    def test_quiet_lot_without_a_reason_leaves_the_question_open(self):
        result = assess_class3_destructive_analysis(_spec(trigger_conditions=_triggers()))
        self.assertEqual(result["verdict"], "waiver-justification-missing")
        self.assertFalse(result["accepted"])

    def test_fired_trigger_with_a_clean_teardown_meets_the_category(self):
        result = assess_class3_destructive_analysis(_spec())
        self.assertEqual(result["verdict"], "sampling-meets-class-three-scope")
        self.assertEqual(result["sample_size"], 5)
        self.assertTrue(result["accepted"])

    def test_major_defect_rejects_the_lot(self):
        result = assess_class3_destructive_analysis(_spec(observations=["die-crack"]))
        self.assertEqual(result["verdict"], "construction-rejected")
        self.assertFalse(result["accepted"])

    def test_minor_defect_alone_does_not_reject_the_lot(self):
        result = assess_class3_destructive_analysis(_spec(observations=["marking-smear"]))
        self.assertTrue(result["accepted"])

    def test_credited_prior_analysis_thins_the_sample_to_the_confirmation_count(self):
        result = assess_class3_destructive_analysis(_spec(prior_analysis=_record()))
        self.assertEqual(result["verdict"], "prior-analysis-credited")
        self.assertEqual(result["sample_size"], 1)

    def test_refused_credit_leaves_the_full_sample_standing(self):
        result = assess_class3_destructive_analysis(
            _spec(prior_analysis=_record(date_code_matches=False))
        )
        self.assertEqual(result["sample_size"], 5)
        self.assertEqual(result["verdict"], "sampling-meets-class-three-scope")

    def test_credited_lot_still_owes_a_confirmation_sample(self):
        result = assess_class3_destructive_analysis(_spec(prior_analysis=_record()))
        self.assertGreaterEqual(result["sample_size"], 1)

    def test_major_defect_outranks_a_credited_prior_analysis(self):
        result = assess_class3_destructive_analysis(
            _spec(prior_analysis=_record(), observations=["package-seal-anomaly"])
        )
        self.assertEqual(result["verdict"], "construction-rejected")

    def test_lot_too_small_to_survive_its_own_sample(self):
        result = assess_class3_destructive_analysis(_spec(lot_size=2))
        self.assertEqual(result["verdict"], "sample-not-feasible")
        self.assertFalse(result["accepted"])

    def test_confirmation_sample_above_the_full_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_destructive_analysis(
                _spec(prior_analysis=_record(), confirmation_sample=9)
            )

    def test_more_observations_than_units_torn_down_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_destructive_analysis(
                _spec(observations=["die-crack", "die-crack", "marking-smear",
                                    "wire-bond-lift", "lead-frame-burr", "die-crack"])
            )

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["observations"]
        with self.assertRaises(ValueError):
            assess_class3_destructive_analysis(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_destructive_analysis(["not", "a", "mapping"])

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_destructive_analysis(_spec(lot_size=0))


if __name__ == "__main__":
    unittest.main()
