"""Contract test for the q7030-pull-off-verification leaf (stdlib unittest)."""

import unittest

from q7030_pull_off_verification_logic import (
    ACCEPT,
    MIN_PULL_OFF_FORCE_N,
    ORIGIN_FLIGHT,
    REVERIFY,
    REWRAP,
    assess_pull_off_verification,
    assess_sample,
    force_margin,
    missing_first_articles,
    required_pull_off_force_n,
    sample_size,
    setup_key,
    validate_sample,
)


def sample(sample_id="S-1", gauge=26, **kw):
    record = {
        "id": sample_id,
        "gauge": gauge,
        "operator_id": "OP-11",
        "tool_id": "TL-3",
        "origin": "process-coupon",
        "first_article": False,
        "measured_force_n": 20.0,
    }
    record.update(kw)
    return record


def lot(n=3, **kw):
    records = [sample("S-%d" % i, **kw) for i in range(1, n + 1)]
    records[0]["first_article"] = True
    return records


class TestForceSchedule(unittest.TestCase):
    def test_every_gauge_owes_a_positive_force(self):
        for gauge in MIN_PULL_OFF_FORCE_N:
            self.assertGreater(required_pull_off_force_n(gauge), 0.0)

    def test_a_coarser_conductor_owes_more_force(self):
        gauges = sorted(MIN_PULL_OFF_FORCE_N)
        for fine, coarse in zip(gauges, gauges[1:]):
            self.assertGreater(
                required_pull_off_force_n(fine), required_pull_off_force_n(coarse)
            )

    def test_unknown_gauge_raises(self):
        with self.assertRaises(ValueError):
            required_pull_off_force_n(18)

    def test_non_integer_gauge_raises(self):
        with self.assertRaises(ValueError):
            required_pull_off_force_n("26")

    def test_margin_of_one_is_a_sample_exactly_on_the_minimum(self):
        self.assertAlmostEqual(
            force_margin(required_pull_off_force_n(26), 26), 1.0, places=9
        )

    def test_negative_measured_force_raises(self):
        with self.assertRaises(ValueError):
            force_margin(-1.0, 26)


class TestSamplingPlan(unittest.TestCase):
    def test_small_lot_owes_three_samples(self):
        self.assertEqual(sample_size(25), 3)

    def test_plan_steps_up_with_the_lot(self):
        self.assertEqual(sample_size(26), 5)
        self.assertEqual(sample_size(91), 8)
        self.assertEqual(sample_size(501), 13)

    def test_plan_is_monotone(self):
        sizes = [sample_size(n) for n in (1, 10, 25, 26, 90, 91, 500, 501, 5000)]
        self.assertEqual(sizes, sorted(sizes))

    def test_a_lot_smaller_than_the_sample_owes_the_whole_lot(self):
        self.assertEqual(sample_size(2), 2)

    def test_zero_lot_raises(self):
        with self.assertRaises(ValueError):
            sample_size(0)

    def test_non_integer_lot_raises(self):
        with self.assertRaises(ValueError):
            sample_size(25.0)


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(["S-1"])

    def test_missing_operator_raises(self):
        record = sample()
        del record["operator_id"]
        with self.assertRaises(ValueError):
            validate_sample(record)

    def test_blank_tool_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(tool_id="  "))

    def test_unknown_origin_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(origin="stores"))

    def test_non_boolean_first_article_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(first_article="yes"))

    def test_missing_force_raises(self):
        record = sample()
        del record["measured_force_n"]
        with self.assertRaises(ValueError):
            validate_sample(record)

    def test_setup_key_is_operator_tool_and_gauge(self):
        self.assertEqual(setup_key(sample()), ("OP-11", "TL-3", 26))


class TestAssessSample(unittest.TestCase):
    def test_comfortable_sample_passes(self):
        result = assess_sample(sample(measured_force_n=20.0))
        self.assertTrue(result["passed"])
        self.assertGreater(result["margin"], 1.4)

    def test_sample_exactly_on_the_minimum_passes(self):
        required = required_pull_off_force_n(26)
        result = assess_sample(sample(measured_force_n=required))
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["margin"], 1.0, places=9)

    def test_sample_under_the_minimum_fails(self):
        result = assess_sample(sample(measured_force_n=12.0))
        self.assertFalse(result["passed"])
        self.assertIn("unwrap-force-below-gauge-minimum", result["findings"])

    def test_flight_hardware_origin_is_a_finding(self):
        result = assess_sample(sample(origin=ORIGIN_FLIGHT))
        self.assertIn("destructive-sample-taken-from-flight-hardware", result["findings"])
        self.assertFalse(result["passed"])

    def test_reported_requirement_matches_the_schedule(self):
        result = assess_sample(sample(gauge=30, measured_force_n=8.0))
        self.assertAlmostEqual(result["required_force_n"], 6.7, places=9)


class TestFirstArticles(unittest.TestCase):
    def test_a_covered_setup_is_not_reported(self):
        self.assertEqual(missing_first_articles(lot(3)), [])

    def test_a_second_operator_owes_its_own_first_article(self):
        records = lot(3) + [sample("S-9", operator_id="OP-22")]
        self.assertEqual(missing_first_articles(records), [("OP-22", "TL-3", 26)])

    def test_a_tool_change_owes_its_own_first_article(self):
        records = lot(3) + [sample("S-9", tool_id="TL-8")]
        self.assertEqual(missing_first_articles(records), [("OP-11", "TL-8", 26)])

    def test_a_gauge_change_owes_its_own_first_article(self):
        records = lot(3) + [sample("S-9", gauge=30, measured_force_n=9.0)]
        self.assertEqual(missing_first_articles(records), [("OP-11", "TL-3", 30)])

    def test_empty_sample_set_raises(self):
        with self.assertRaises(ValueError):
            missing_first_articles([])


class TestLotVerdict(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        summary = assess_pull_off_verification(25, lot(3))
        self.assertEqual(summary["disposition"], ACCEPT)
        self.assertTrue(summary["accepted"])
        self.assertEqual(summary["samples_owed"], 3)

    def test_a_weak_sample_rejects_the_lot(self):
        records = lot(3)
        records[2]["measured_force_n"] = 5.0
        summary = assess_pull_off_verification(25, records)
        self.assertEqual(summary["disposition"], REWRAP)
        self.assertEqual(summary["below_minimum_ids"], ["S-3"])

    def test_too_few_samples_hold_the_lot_for_reverification(self):
        summary = assess_pull_off_verification(200, lot(3))
        self.assertEqual(summary["disposition"], REVERIFY)
        self.assertIn("sample-count-below-plan", summary["lot_findings"])

    def test_an_uncovered_setup_holds_the_lot(self):
        records = [sample("S-%d" % i) for i in range(1, 4)]
        summary = assess_pull_off_verification(25, records)
        self.assertEqual(summary["disposition"], REVERIFY)
        self.assertIn("setup-without-a-first-article-wrap", summary["lot_findings"])

    def test_worst_margin_is_the_weakest_sample(self):
        records = lot(3)
        records[1]["measured_force_n"] = 14.0
        summary = assess_pull_off_verification(25, records)
        self.assertAlmostEqual(summary["worst_margin"], 14.0 / 13.3, places=9)

    def test_duplicate_sample_ids_raise(self):
        records = lot(2)
        records[1]["id"] = records[0]["id"]
        with self.assertRaises(ValueError):
            assess_pull_off_verification(25, records)

    def test_empty_samples_raise(self):
        with self.assertRaises(ValueError):
            assess_pull_off_verification(25, [])

    def test_non_list_samples_raise(self):
        with self.assertRaises(ValueError):
            assess_pull_off_verification(25, sample())


if __name__ == "__main__":
    unittest.main()
