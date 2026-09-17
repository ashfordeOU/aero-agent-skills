"""Contract tests for the Table 8-14 legacy class 2 lot acceptance logic.

The cases follow the workflow one step at a time: the banded sampling plan and
the lot too small to yield it, group validation under the accept-on-zero rule,
the provenance of the devices sampled, the population the campaign consumes
against the quantity to be delivered, the single admissible resubmission and
its preconditions, and the disposition that carries them. Each step is
exercised on both sides of its limit, so a review of the record shows what was
judged and not only the verdict.
"""

import unittest

from q6013_legacy_class_2_acceptance_table_logic import (
    ACCEPTANCE_GROUPS,
    LARGE_LOT_SAMPLE,
    LIMIT_TOLERANCE,
    LOT_SIZE_BANDS,
    MAX_RESUBMISSIONS,
    assess_legacy_class_2_acceptance,
    consumption_balance,
    group_verdict,
    resubmission_decision,
    sample_provenance,
    sample_size_for_lot,
    validate_group,
)


def _group(name, **extra):
    record = {"group": name}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lot_size": 400,
        "groups": [_group(name) for name in ACCEPTANCE_GROUPS],
        "screened_population": 400,
        "required_quantity": 250,
        "lot_date_code": "2504",
        "sample_date_codes": ["2504"] * 20,
        "attempt": 1,
    }
    spec.update(overrides)
    return spec


class SamplingPlanTests(unittest.TestCase):
    def test_a_small_lot_reads_the_first_band(self):
        plan = sample_size_for_lot(20)
        self.assertEqual(plan["sample_size"], LOT_SIZE_BANDS[0][1])
        self.assertEqual(plan["band_upper"], LOT_SIZE_BANDS[0][0])

    def test_a_lot_on_a_band_edge_stays_in_that_band(self):
        edge, devices = LOT_SIZE_BANDS[1]
        self.assertEqual(sample_size_for_lot(edge)["sample_size"], devices)

    def test_a_lot_one_device_past_a_band_edge_moves_up(self):
        edge = LOT_SIZE_BANDS[1][0]
        self.assertEqual(
            sample_size_for_lot(edge + 1)["sample_size"], LOT_SIZE_BANDS[2][1]
        )

    def test_a_lot_beyond_the_last_band_takes_the_large_lot_sample(self):
        plan = sample_size_for_lot(LOT_SIZE_BANDS[-1][0] + 1)
        self.assertEqual(plan["sample_size"], LARGE_LOT_SAMPLE)
        self.assertIsNone(plan["band_upper"])

    def test_a_lot_too_small_to_yield_the_plan_is_reported(self):
        plan = sample_size_for_lot(2)
        self.assertFalse(plan["drawable"])

    def test_a_zero_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            sample_size_for_lot(0)


class GroupValidationTests(unittest.TestCase):
    def test_a_group_defaults_to_the_planned_sample(self):
        record = validate_group(_group("solderability"), 400)
        self.assertEqual(record["sample_size"], sample_size_for_lot(400)["sample_size"])
        self.assertEqual(record["sample_shortfall"], 0)

    def test_an_undersized_sample_carries_a_shortfall(self):
        record = validate_group(_group("endurance-life-test", sample_size=5), 400)
        self.assertEqual(
            record["sample_shortfall"],
            sample_size_for_lot(400)["sample_size"] - 5,
        )

    def test_an_accept_number_above_zero_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(_group("thermal-shock-and-seal", accept_number=1), 400)

    def test_a_group_outside_the_table_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(_group("radiation-acceptance"), 400)

    def test_sampling_more_devices_than_the_lot_holds_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(_group("solderability", sample_size=500), 400)

    def test_more_failures_than_devices_sampled_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(
                _group("solderability", sample_size=5, failures=6), 400
            )

    def test_non_mapping_group_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(["solderability"], 400)


class GroupVerdictTests(unittest.TestCase):
    def test_a_clean_group_is_accepted(self):
        record = group_verdict(_group("physical-dimensions"), 400)
        self.assertTrue(record["accepted"])

    def test_one_failure_rejects_an_accept_on_zero_group(self):
        record = group_verdict(_group("physical-dimensions", failures=1), 400)
        self.assertFalse(record["within_accept_number"])
        self.assertFalse(record["accepted"])

    def test_a_sample_shortfall_rejects_an_otherwise_clean_group(self):
        record = group_verdict(_group("physical-dimensions", sample_size=4), 400)
        self.assertFalse(record["sample_met"])
        self.assertFalse(record["accepted"])


class ProvenanceTests(unittest.TestCase):
    def test_a_sample_drawn_from_the_lot_is_accepted(self):
        result = sample_provenance(["2504", "2504"], "2504")
        self.assertTrue(result["accepted"])

    def test_a_foreign_date_code_is_named(self):
        result = sample_provenance(["2504", "2350"], "2504")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["foreign_date_codes"], ("2350",))

    def test_an_empty_sample_list_is_refused(self):
        with self.assertRaises(ValueError):
            sample_provenance([], "2504")

    def test_a_blank_lot_date_code_is_refused(self):
        with self.assertRaises(ValueError):
            sample_provenance(["2504"], "   ")


class ConsumptionTests(unittest.TestCase):
    def test_the_remaining_population_drops_by_what_was_consumed(self):
        result = consumption_balance(400, 65, 250)
        self.assertEqual(result["remaining"], 335)
        self.assertTrue(result["accepted"])

    def test_an_exactly_sufficient_remainder_is_accepted(self):
        self.assertTrue(consumption_balance(400, 150, 250)["accepted"])

    def test_a_short_remainder_reports_the_shortfall(self):
        result = consumption_balance(400, 200, 250)
        self.assertEqual(result["shortfall"], 50)
        self.assertFalse(result["accepted"])

    def test_consuming_more_than_the_screened_population_is_refused(self):
        with self.assertRaises(ValueError):
            consumption_balance(100, 101, 50)


class ResubmissionTests(unittest.TestCase):
    def test_a_first_attempt_needs_no_preconditions(self):
        self.assertTrue(resubmission_decision(1)["admissible"])

    def test_a_prepared_resubmission_is_admissible(self):
        result = resubmission_decision(2, mechanism_identified=True, rescreened=True)
        self.assertEqual(result["resubmissions"], MAX_RESUBMISSIONS)
        self.assertTrue(result["admissible"])

    def test_a_resubmission_without_a_mechanism_is_refused(self):
        result = resubmission_decision(2, mechanism_identified=False, rescreened=True)
        self.assertFalse(result["admissible"])

    def test_a_resubmission_without_a_rescreen_is_refused(self):
        result = resubmission_decision(2, mechanism_identified=True, rescreened=False)
        self.assertFalse(result["admissible"])

    def test_a_second_resubmission_is_refused_however_well_prepared(self):
        result = resubmission_decision(3, mechanism_identified=True, rescreened=True)
        self.assertFalse(result["admissible"])

    def test_a_zero_attempt_is_refused(self):
        with self.assertRaises(ValueError):
            resubmission_decision(0)

    def test_a_non_boolean_precondition_is_refused(self):
        with self.assertRaises(ValueError):
            resubmission_decision(2, mechanism_identified="yes", rescreened=True)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_campaign_accepts_the_lot(self):
        result = assess_legacy_class_2_acceptance(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-lot")
        self.assertEqual(result["findings"], [])

    def test_one_failure_holds_the_lot_and_names_the_group(self):
        spec = _spec()
        spec["groups"][2] = _group("mechanical-shock-and-vibration", failures=1)
        result = assess_legacy_class_2_acceptance(spec)
        self.assertEqual(
            result["rejecting_groups"], ["mechanical-shock-and-vibration"]
        )
        self.assertEqual(result["disposition"], "hold-lot")

    def test_a_skipped_group_is_named(self):
        spec = _spec()
        spec["groups"] = spec["groups"][:3]
        result = assess_legacy_class_2_acceptance(spec)
        self.assertIn("solderability", result["absent_groups"])
        self.assertFalse(result["accepted"])

    def test_a_foreign_sample_holds_an_otherwise_clean_campaign(self):
        result = assess_legacy_class_2_acceptance(
            _spec(sample_date_codes=["2504"] * 19 + ["2350"])
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("not the lot being accepted" in item for item in result["findings"])
        )

    def test_consumption_can_leave_the_lot_short_of_the_order(self):
        result = assess_legacy_class_2_acceptance(
            _spec(screened_population=100, lot_size=100, required_quantity=95)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("short of" in item for item in result["findings"]))

    def test_the_consumed_total_is_the_sum_of_the_group_samples(self):
        result = assess_legacy_class_2_acceptance(_spec())
        self.assertEqual(
            result["consumed"],
            sum(record["sample_size"] for record in result["groups"]),
        )

    def test_a_second_resubmission_holds_a_clean_campaign(self):
        result = assess_legacy_class_2_acceptance(
            _spec(attempt=3, mechanism_identified=True, rescreened=True)
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["resubmission"]["admissible"])

    def test_a_lot_too_small_for_the_plan_is_reported(self):
        spec = _spec(
            lot_size=2,
            groups=[_group(name, sample_size=1) for name in ACCEPTANCE_GROUPS],
            sample_date_codes=["2504"],
        )
        del spec["screened_population"]
        del spec["required_quantity"]
        result = assess_legacy_class_2_acceptance(spec)
        self.assertFalse(result["plan"]["drawable"])
        self.assertFalse(result["accepted"])
        self.assertTrue(any("cannot yield" in item for item in result["findings"]))

    def test_consuming_more_than_the_screened_population_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_acceptance(
                _spec(screened_population=10, required_quantity=5)
            )

    def test_a_repeated_group_is_refused(self):
        spec = _spec()
        spec["groups"].append(_group("solderability"))
        with self.assertRaises(ValueError):
            assess_legacy_class_2_acceptance(spec)

    def test_an_empty_group_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_acceptance(_spec(groups=[]))

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_acceptance(["not", "a", "mapping"])

    def test_named_constants_are_representation_sized_or_bounded(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertEqual(MAX_RESUBMISSIONS, 1)
        self.assertEqual(len(ACCEPTANCE_GROUPS), 5)
        uppers = [band[0] for band in LOT_SIZE_BANDS]
        self.assertEqual(uppers, sorted(uppers))
        self.assertGreater(LARGE_LOT_SAMPLE, LOT_SIZE_BANDS[-1][1])


if __name__ == "__main__":
    unittest.main()
