"""Contract tests for the Table 8-11 legacy lot acceptance list logic.

The cases follow the workflow one step at a time: the screened quantity the
samples come from, the band table that resolves each subgroup's sample and
accept number, list coverage, the per-subgroup verdict with its single
doubled retest, the parts the destructive subgroups consume, and the
deliverable quantity and disposition the lot ends with. Band boundaries are
exercised on both sides so the table is pinned, not sampled.
"""

import unittest

from q6013_legacy_class_1_acceptance_table_logic import (
    DESTRUCTIVE_SUBGROUPS,
    MAX_RETESTS,
    REQUIRED_SUBGROUPS,
    RETESTABLE_SUBGROUPS,
    SAMPLING_BANDS,
    acceptance_coverage,
    assess_legacy_acceptance_table,
    deliverable_quantity,
    destructive_consumption,
    resolve_subgroup_sample,
    sampling_plan,
    subgroup_verdict,
    validate_screened_quantity,
)

QUANTITY = 400


def _entry(subgroup, failures=0, **extra):
    record = {"subgroup": subgroup, "failures": failures}
    record.update(extra)
    return record


def _full_list(**per_subgroup):
    return [_entry(s, **per_subgroup.get(s, {})) for s in REQUIRED_SUBGROUPS]


def _spec(**overrides):
    spec = {"screened_quantity": QUANTITY, "entries": _full_list()}
    spec.update(overrides)
    return spec


class ScreenedQuantityTests(unittest.TestCase):
    def test_a_positive_quantity_is_returned(self):
        self.assertEqual(validate_screened_quantity(QUANTITY), QUANTITY)

    def test_a_single_part_quantity_is_allowed(self):
        self.assertEqual(validate_screened_quantity(1), 1)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_screened_quantity(0)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_screened_quantity(-4)

    def test_float_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_screened_quantity(400.0)

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_screened_quantity(True)


class SamplingPlanTests(unittest.TestCase):
    def test_the_smallest_band_draws_the_smallest_sample(self):
        self.assertEqual(sampling_plan(10)["sample_size"], 3)

    def test_a_quantity_on_a_band_edge_stays_in_the_lower_band(self):
        self.assertEqual(sampling_plan(25)["sample_size"], 3)

    def test_one_part_past_the_edge_moves_up_a_band(self):
        self.assertEqual(sampling_plan(26)["sample_size"], 5)

    def test_two_quantities_in_one_band_draw_the_same_sample(self):
        self.assertEqual(
            sampling_plan(60)["sample_size"], sampling_plan(140)["sample_size"]
        )

    def test_the_open_ended_band_covers_a_very_large_lot(self):
        self.assertEqual(sampling_plan(50000)["sample_size"], 32)

    def test_small_bands_accept_on_zero(self):
        self.assertEqual(sampling_plan(400)["accept_number"], 0)

    def test_every_band_is_reachable(self):
        for low, _high, sample, _accept in SAMPLING_BANDS:
            self.assertEqual(sampling_plan(low)["sample_size"], sample)

    def test_a_zero_quantity_has_no_band(self):
        with self.assertRaises(ValueError):
            sampling_plan(0)


class SampleResolutionTests(unittest.TestCase):
    def test_a_subgroup_takes_the_plan_sample_by_default(self):
        record = resolve_subgroup_sample(_entry("die-shear"), QUANTITY)
        self.assertEqual(record["sample_size"], 13)
        self.assertFalse(record["enlarged"])

    def test_a_declared_enlargement_is_taken_as_written(self):
        record = resolve_subgroup_sample(_entry("die-shear", sample_size=20), QUANTITY)
        self.assertEqual(record["sample_size"], 20)
        self.assertTrue(record["enlarged"])

    def test_a_declared_sample_below_the_plan_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_subgroup_sample(_entry("die-shear", sample_size=5), QUANTITY)

    def test_a_sample_equal_to_the_plan_is_not_an_enlargement(self):
        record = resolve_subgroup_sample(_entry("die-shear", sample_size=13), QUANTITY)
        self.assertFalse(record["enlarged"])

    def test_an_accept_number_above_the_plan_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_subgroup_sample(_entry("die-shear", accept_number=2), QUANTITY)

    def test_a_tighter_accept_number_is_allowed(self):
        record = resolve_subgroup_sample(_entry("die-shear", accept_number=0), 800)
        self.assertEqual(record["accept_number"], 0)
        self.assertEqual(record["plan_accept_number"], 1)

    def test_a_sample_larger_than_the_screened_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_subgroup_sample(_entry("die-shear", sample_size=40), 20)

    def test_a_subgroup_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_subgroup_sample({"failures": 0}, QUANTITY)


class CoverageTests(unittest.TestCase):
    def test_a_full_list_is_complete(self):
        coverage = acceptance_coverage(_full_list())
        self.assertTrue(coverage["complete"])

    def test_a_missing_subgroup_is_named(self):
        entries = [e for e in _full_list() if e["subgroup"] != "die-shear"]
        coverage = acceptance_coverage(entries)
        self.assertIn("die-shear", coverage["missing"])

    def test_a_duplicated_subgroup_is_named(self):
        entries = _full_list() + [_entry("solderability")]
        coverage = acceptance_coverage(entries)
        self.assertEqual(coverage["duplicated"], ["solderability"])

    def test_an_added_subgroup_does_not_block_coverage(self):
        entries = _full_list() + [_entry("board-mount-shear")]
        coverage = acceptance_coverage(entries)
        self.assertEqual(coverage["unrecognized"], ["board-mount-shear"])
        self.assertTrue(coverage["complete"])

    def test_an_empty_list_is_refused(self):
        with self.assertRaises(ValueError):
            acceptance_coverage([])


class SubgroupVerdictTests(unittest.TestCase):
    def test_a_clean_subgroup_accepts(self):
        record = subgroup_verdict(_entry("electrical-end-points"), QUANTITY)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_a_failure_against_an_accept_on_zero_plan_fails(self):
        record = subgroup_verdict(_entry("die-shear", failures=1), QUANTITY)
        self.assertFalse(record["accepted"])
        self.assertEqual(len(record["findings"]), 1)

    def test_a_destructive_subgroup_is_marked_as_one(self):
        record = subgroup_verdict(_entry("internal-water-vapour"), QUANTITY)
        self.assertTrue(record["destructive"])

    def test_a_non_destructive_subgroup_is_not_marked(self):
        record = subgroup_verdict(_entry("electrical-end-points"), QUANTITY)
        self.assertFalse(record["destructive"])

    def test_a_retest_doubles_the_sample_and_can_recover_the_subgroup(self):
        record = subgroup_verdict(
            _entry("electrical-end-points", failures=1, retest={"failures": 0}), QUANTITY
        )
        self.assertTrue(record["accepted"])
        self.assertEqual(record["retest"]["sample_size"], 26)
        self.assertEqual(record["parts_drawn"], 39)

    def test_a_failed_retest_leaves_the_subgroup_failed(self):
        record = subgroup_verdict(
            _entry("electrical-end-points", failures=1, retest={"failures": 2}), QUANTITY
        )
        self.assertFalse(record["accepted"])
        self.assertEqual(len(record["findings"]), 1)

    def test_a_retest_on_a_subgroup_that_takes_none_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(_entry("die-shear", failures=1, retest={"failures": 0}), QUANTITY)

    def test_a_retest_after_an_accepted_first_sample_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(
                _entry("electrical-end-points", failures=0, retest={"failures": 0}), QUANTITY
            )

    def test_a_second_retest_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(
                _entry(
                    "electrical-end-points",
                    failures=1,
                    retest={"failures": 0, "attempt": MAX_RETESTS + 1},
                ),
                QUANTITY,
            )

    def test_a_doubled_sample_larger_than_the_lot_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(
                _entry("electrical-end-points", failures=1, retest={"failures": 0}), 5
            )

    def test_more_failures_than_the_sample_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(_entry("die-shear", failures=20), QUANTITY)

    def test_a_subgroup_without_a_failure_count_is_refused(self):
        with self.assertRaises(ValueError):
            subgroup_verdict({"subgroup": "die-shear"}, QUANTITY)

    def test_every_retestable_subgroup_is_also_a_declared_subgroup(self):
        for subgroup in RETESTABLE_SUBGROUPS:
            self.assertIn(subgroup, REQUIRED_SUBGROUPS)


class ConsumptionTests(unittest.TestCase):
    def test_only_destructive_subgroups_consume_parts(self):
        verdicts = [subgroup_verdict(e, QUANTITY) for e in _full_list()]
        expected = 13 * len(DESTRUCTIVE_SUBGROUPS)
        self.assertEqual(destructive_consumption(verdicts), expected)

    def test_a_retest_on_a_destructive_subgroup_adds_to_the_consumption(self):
        entries = _full_list(
            **{"solderability": {"failures": 1, "retest": {"failures": 0}}}
        )
        verdicts = [subgroup_verdict(e, QUANTITY) for e in entries]
        expected = 13 * len(DESTRUCTIVE_SUBGROUPS) + 26
        self.assertEqual(destructive_consumption(verdicts), expected)

    def test_a_non_sequence_of_verdicts_is_refused(self):
        with self.assertRaises(ValueError):
            destructive_consumption("die-shear")

    def test_the_deliverable_quantity_drops_by_what_was_consumed(self):
        self.assertEqual(deliverable_quantity(400, 65), 335)

    def test_consuming_the_whole_quantity_leaves_nothing(self):
        self.assertEqual(deliverable_quantity(65, 65), 0)

    def test_consuming_more_than_the_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            deliverable_quantity(50, 65)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_clean_list_accepts_the_lot(self):
        result = assess_legacy_acceptance_table(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-lot")

    def test_the_deliverable_quantity_excludes_the_destructive_samples(self):
        result = assess_legacy_acceptance_table(_spec())
        self.assertEqual(
            result["deliverable_quantity"], QUANTITY - 13 * len(DESTRUCTIVE_SUBGROUPS)
        )

    def test_a_failed_subgroup_rejects_the_lot(self):
        entries = _full_list(**{"die-shear": {"failures": 1}})
        result = assess_legacy_acceptance_table(_spec(entries=entries))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failing_subgroups"], ["die-shear"])

    def test_every_failing_subgroup_is_named_not_just_the_first(self):
        entries = _full_list(
            **{"die-shear": {"failures": 1}, "bond-strength": {"failures": 2}}
        )
        result = assess_legacy_acceptance_table(_spec(entries=entries))
        self.assertEqual(sorted(result["failing_subgroups"]), ["bond-strength", "die-shear"])

    def test_a_recovered_retest_accepts_the_lot_with_an_advisory(self):
        entries = _full_list(
            **{"electrical-end-points": {"failures": 1, "retest": {"failures": 0}}}
        )
        result = assess_legacy_acceptance_table(_spec(entries=entries))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_missing_subgroup_rejects_the_lot(self):
        entries = [e for e in _full_list() if e["subgroup"] != "seal-fine-and-gross"]
        result = assess_legacy_acceptance_table(_spec(entries=entries))
        self.assertFalse(result["accepted"])

    def test_an_enlarged_sample_is_reported_as_an_advisory(self):
        entries = _full_list(**{"die-shear": {"sample_size": 20}})
        result = assess_legacy_acceptance_table(_spec(entries=entries))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_small_lot_draws_a_small_sample_and_still_delivers(self):
        result = assess_legacy_acceptance_table(_spec(screened_quantity=60))
        self.assertEqual(result["parts_consumed"], 8 * len(DESTRUCTIVE_SUBGROUPS))
        self.assertEqual(result["deliverable_quantity"], 60 - 8 * len(DESTRUCTIVE_SUBGROUPS))

    def test_a_lot_consumed_in_full_is_reported_as_an_advisory(self):
        result = assess_legacy_acceptance_table(_spec(screened_quantity=30))
        self.assertEqual(result["deliverable_quantity"], 0)
        self.assertIn(
            "the acceptance programme consumed the whole screened quantity",
            result["advisories"],
        )

    def test_a_lot_too_small_for_its_destructive_samples_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_acceptance_table(_spec(screened_quantity=10))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_legacy_acceptance_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_legacy_acceptance_table(["screened_quantity"])

    def test_one_retest_is_the_limit(self):
        self.assertEqual(MAX_RETESTS, 1)


if __name__ == "__main__":
    unittest.main()
