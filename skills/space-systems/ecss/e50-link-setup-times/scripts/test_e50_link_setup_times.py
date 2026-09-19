"""Contract tests for the clause 5.6.8 link setup time logic."""

import unittest

from e50_link_setup_times_logic import (
    ERODES_PASS,
    EXCEEDS_BUDGET,
    WITHIN_BUDGET,
    assess_link_setup,
    dominant_stage,
    handshake_delay_s,
    normalize_stages,
    one_way_delay_s,
    pass_share,
    required_reduction_s,
    setup_time_s,
    stage_total_s,
    usable_pass_s,
    validate_count,
    validate_duration,
    validate_fraction,
    validate_positive_duration,
)

STAGES = [
    ("carrier-acquisition", 4.0),
    ("symbol-synchronisation", 2.0),
    ("frame-synchronisation", 1.5),
    ("negotiation", 0.5),
]
PASS_S = 600.0


class ValidationTests(unittest.TestCase):
    def test_zero_duration_accepted(self):
        self.assertAlmostEqual(validate_duration(0), 0.0, places=9)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(-0.1)

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(True)

    def test_text_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration("4.0")

    def test_nan_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(float("nan"))

    def test_zero_positive_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_duration(0.0)

    def test_fractional_exchange_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(1.5)

    def test_negative_exchange_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(-1)

    def test_zero_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(0.0)

    def test_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.2)


class StageTests(unittest.TestCase):
    def test_stages_sum(self):
        self.assertAlmostEqual(stage_total_s(STAGES), 8.0, places=9)

    def test_mapping_entries_accepted(self):
        mapped = [{"name": "acq", "seconds": 3.0}, {"name": "sync", "seconds": 1.0}]
        self.assertAlmostEqual(stage_total_s(mapped), 4.0, places=9)

    def test_empty_stage_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stages([])

    def test_duplicate_stage_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stages([("acq", 1.0), ("acq", 2.0)])

    def test_negative_stage_duration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stages([("acq", -1.0)])

    def test_unnamed_stage_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stages([("", 1.0)])

    def test_dominant_stage_is_the_longest(self):
        self.assertEqual(dominant_stage(STAGES)[0], "carrier-acquisition")

    def test_dominant_stage_tie_goes_to_the_first_declared(self):
        self.assertEqual(dominant_stage([("a", 2.0), ("b", 2.0)])[0], "a")


class PropagationTests(unittest.TestCase):
    def test_one_way_delay_of_a_geostationary_range(self):
        self.assertAlmostEqual(one_way_delay_s(35786.0), 35786000.0 / 299792458.0, places=9)

    def test_zero_range_costs_nothing(self):
        self.assertAlmostEqual(one_way_delay_s(0.0), 0.0, places=9)

    def test_handshake_costs_two_delays_per_exchange(self):
        self.assertAlmostEqual(handshake_delay_s(3, 0.25), 1.5, places=9)

    def test_no_exchange_costs_nothing(self):
        self.assertAlmostEqual(handshake_delay_s(0, 0.25), 0.0, places=9)

    def test_setup_adds_stage_work_and_propagation(self):
        self.assertAlmostEqual(setup_time_s(STAGES, 2, 0.5), 10.0, places=9)


class WindowTests(unittest.TestCase):
    def test_pass_share_is_the_ratio(self):
        self.assertAlmostEqual(pass_share(60.0, PASS_S), 0.1, places=9)

    def test_usable_pass_is_what_is_left(self):
        self.assertAlmostEqual(usable_pass_s(60.0, PASS_S), 540.0, places=9)

    def test_setup_longer_than_the_pass_leaves_nothing(self):
        self.assertAlmostEqual(usable_pass_s(700.0, PASS_S), 0.0, places=9)

    def test_zero_pass_duration_rejected(self):
        with self.assertRaises(ValueError):
            pass_share(10.0, 0.0)

    def test_reduction_is_zero_inside_the_budget(self):
        self.assertAlmostEqual(required_reduction_s(8.0, 10.0), 0.0, places=9)

    def test_reduction_is_the_overshoot(self):
        self.assertAlmostEqual(required_reduction_s(14.0, 10.0), 4.0, places=9)


class AssessTests(unittest.TestCase):
    def test_setup_inside_both_limits_passes(self):
        result = assess_link_setup(STAGES, 10.0, PASS_S)
        self.assertEqual(result["verdict"], WITHIN_BUDGET)
        self.assertTrue(result["within_budget"])

    def test_setup_exactly_on_the_budget_passes(self):
        result = assess_link_setup(STAGES, 8.0, PASS_S)
        self.assertAlmostEqual(result["setup_time_s"], result["budget_s"], places=9)
        self.assertEqual(result["verdict"], WITHIN_BUDGET)

    def test_setup_over_the_budget_fails(self):
        result = assess_link_setup(STAGES, 5.0, PASS_S)
        self.assertEqual(result["verdict"], EXCEEDS_BUDGET)
        self.assertAlmostEqual(result["required_reduction_s"], 3.0, places=9)

    def test_setup_inside_the_budget_can_still_eat_the_pass(self):
        result = assess_link_setup(STAGES, 10.0, 40.0)
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["verdict"], ERODES_PASS)

    def test_pass_share_exactly_on_the_limit_passes(self):
        result = assess_link_setup(STAGES, 10.0, 80.0, max_pass_share=0.1)
        self.assertAlmostEqual(result["pass_share"], 0.1, places=9)
        self.assertEqual(result["verdict"], WITHIN_BUDGET)

    def test_handshake_propagation_is_reported_separately(self):
        result = assess_link_setup(STAGES, 20.0, PASS_S, exchanges=4, one_way_s=0.25)
        self.assertAlmostEqual(result["handshake_delay_s"], 2.0, places=9)
        self.assertAlmostEqual(result["stage_total_s"], 8.0, places=9)

    def test_propagation_dominated_setup_is_called_out(self):
        result = assess_link_setup(
            [("acq", 1.0)], 60.0, PASS_S, exchanges=5, one_way_s=1.2
        )
        self.assertTrue(any("fewer exchanges" in f for f in result["findings"]))

    def test_clean_setup_reports_no_findings(self):
        self.assertEqual(assess_link_setup(STAGES, 10.0, PASS_S)["findings"], [])

    def test_dominant_stage_is_carried_in_the_result(self):
        result = assess_link_setup(STAGES, 10.0, PASS_S)
        self.assertEqual(result["dominant_stage"], "carrier-acquisition")
        self.assertAlmostEqual(result["dominant_stage_s"], 4.0, places=9)

    def test_usable_pass_is_carried_in_the_result(self):
        result = assess_link_setup(STAGES, 10.0, PASS_S)
        self.assertAlmostEqual(result["usable_pass_s"], 592.0, places=9)

    def test_stated_reduction_actually_meets_the_budget(self):
        result = assess_link_setup(STAGES, 5.0, PASS_S)
        shaved = [("carrier-acquisition", 4.0 - result["required_reduction_s"])] + list(STAGES[1:])
        self.assertEqual(assess_link_setup(shaved, 5.0, PASS_S)["verdict"], WITHIN_BUDGET)

    def test_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_setup(STAGES, 0.0, PASS_S)

    def test_bad_share_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_link_setup(STAGES, 10.0, PASS_S, max_pass_share=0.0)


if __name__ == "__main__":
    unittest.main()
