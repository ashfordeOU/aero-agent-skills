"""Contract tests for the clause 5.3.9 Class 2 teardown analysis logic."""

import unittest

from q60_class_2_destructive_physical_analysis_logic import (
    CONFIRMATION_SAMPLE,
    DEFAULT_CREDIT_WINDOW_MONTHS,
    DEFAULT_MINOR_ALLOWANCE,
    DEFAULT_SAMPLE_FRACTION,
    DEFAULT_VOID_LIMIT_FRACTION,
    FINDING_CATEGORIES,
    MAXIMUM_SAMPLE,
    MINIMUM_SAMPLE,
    WIRE_BOND_MINIMUM_PULL_G,
    assess_class_2_teardown,
    categorize_finding,
    die_attach_void_fraction,
    evaluate_bond_pulls,
    minimum_pull_force,
    partition_by_date_code,
    prior_teardown_credited,
    summarize_findings,
    teardown_plan,
    teardown_sample_size,
    void_within_limit,
)

REGISTER = {
    "cracked-die": "critical",
    "open-bond-lift": "critical",
    "voided-die-attach": "major",
    "misaligned-die": "major",
    "surface-contamination": "minor",
    "marking-smear": "minor",
}


def units(count, date_code):
    return [
        {"serial": "%s-%05d" % (date_code, index), "date_code": date_code}
        for index in range(count)
    ]


class DateCodePartitionTests(unittest.TestCase):
    def test_one_date_code_makes_one_group(self):
        groups = partition_by_date_code(units(12, "2338"))
        self.assertEqual(list(groups), ["2338"])

    def test_two_date_codes_stay_apart(self):
        groups = partition_by_date_code(units(9, "2338") + units(5, "2405"))
        self.assertEqual(sorted(groups), ["2338", "2405"])
        self.assertEqual(len(groups["2338"]), 9)
        self.assertEqual(len(groups["2405"]), 5)

    def test_date_code_whitespace_is_normalized(self):
        groups = partition_by_date_code(
            [
                {"serial": "u1", "date_code": " 2338 "},
                {"serial": "u2", "date_code": "2338"},
            ]
        )
        self.assertEqual(len(groups["2338"]), 2)

    def test_repeated_serial_refused(self):
        with self.assertRaises(ValueError):
            partition_by_date_code(
                [
                    {"serial": "u1", "date_code": "2338"},
                    {"serial": "u1", "date_code": "2405"},
                ]
            )

    def test_missing_date_code_refused(self):
        with self.assertRaises(ValueError):
            partition_by_date_code([{"serial": "u1"}])

    def test_empty_shipment_refused(self):
        with self.assertRaises(ValueError):
            partition_by_date_code([])


class SampleSizingTests(unittest.TestCase):
    def test_small_group_takes_the_minimum(self):
        self.assertEqual(teardown_sample_size(40), MINIMUM_SAMPLE)

    def test_fraction_landing_on_an_integer_does_not_round_up(self):
        self.assertEqual(teardown_sample_size(150), 3)

    def test_large_group_is_capped(self):
        self.assertEqual(teardown_sample_size(4000), MAXIMUM_SAMPLE)

    def test_group_under_the_minimum_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(1)

    def test_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(200, 1.4)

    def test_cap_below_the_floor_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(200, 0.02, 4, 2)

    def test_default_fraction_is_two_percent(self):
        self.assertAlmostEqual(DEFAULT_SAMPLE_FRACTION, 0.02, places=9)


class PriorTeardownCreditTests(unittest.TestCase):
    def test_recent_teardown_is_credited(self):
        self.assertTrue(prior_teardown_credited(4.0))

    def test_teardown_exactly_on_the_window_is_still_credited(self):
        self.assertTrue(
            prior_teardown_credited(
                float(DEFAULT_CREDIT_WINDOW_MONTHS), DEFAULT_CREDIT_WINDOW_MONTHS
            )
        )

    def test_teardown_past_the_window_is_not_credited(self):
        self.assertFalse(prior_teardown_credited(18.0))

    def test_negative_age_refused(self):
        with self.assertRaises(ValueError):
            prior_teardown_credited(-1.0)

    def test_window_must_be_positive(self):
        with self.assertRaises(ValueError):
            prior_teardown_credited(3.0, 0.0)


class TeardownPlanTests(unittest.TestCase):
    def test_every_group_owes_a_teardown(self):
        plan = teardown_plan(partition_by_date_code(units(200, "2338") + units(60, "2405")))
        self.assertEqual(sorted(plan), ["2338", "2405"])

    def test_sample_scales_with_the_group(self):
        plan = teardown_plan({"2338": 200, "2405": 60})
        self.assertEqual(plan["2338"]["sample_size"], 4)
        self.assertEqual(plan["2405"]["sample_size"], 2)

    def test_credited_group_drops_to_a_confirmation_sample(self):
        plan = teardown_plan({"2338": 200}, {"2338": 6.0})
        self.assertTrue(plan["2338"]["credited"])
        self.assertEqual(plan["2338"]["sample_size"], CONFIRMATION_SAMPLE)

    def test_stale_prior_teardown_earns_no_credit(self):
        plan = teardown_plan({"2338": 200}, {"2338": 20.0})
        self.assertFalse(plan["2338"]["credited"])
        self.assertEqual(plan["2338"]["sample_size"], 4)

    def test_spare_units_are_reported(self):
        plan = teardown_plan({"2338": 200}, None, {"2338": 150})
        self.assertEqual(plan["2338"]["spare_units"], 50)

    def test_demand_eating_the_sample_refused(self):
        with self.assertRaises(ValueError):
            teardown_plan({"2338": 200}, None, {"2338": 199})

    def test_demand_above_the_delivery_refused(self):
        with self.assertRaises(ValueError):
            teardown_plan({"2338": 200}, None, {"2338": 260})

    def test_empty_group_map_refused(self):
        with self.assertRaises(ValueError):
            teardown_plan({})


class FindingCategoryTests(unittest.TestCase):
    def test_three_categories_are_carried(self):
        self.assertEqual(FINDING_CATEGORIES, ("critical", "major", "minor"))

    def test_critical_code_categorized(self):
        self.assertEqual(categorize_finding(REGISTER, "cracked-die"), "critical")

    def test_minor_code_categorized(self):
        self.assertEqual(categorize_finding(REGISTER, "marking-smear"), "minor")

    def test_unregistered_code_refused(self):
        with self.assertRaises(ValueError):
            categorize_finding(REGISTER, "something-odd")

    def test_unknown_category_value_refused(self):
        with self.assertRaises(ValueError):
            categorize_finding({"cracked-die": "severe"}, "cracked-die")

    def test_observations_counted_by_category(self):
        summary = summarize_findings(
            [
                {"date_code": "2338", "finding_code": "cracked-die"},
                {"date_code": "2338", "finding_code": "marking-smear"},
                {"date_code": "2405", "finding_code": "misaligned-die"},
            ],
            REGISTER,
        )
        self.assertEqual(summary["critical_count"], 1)
        self.assertEqual(summary["major_count"], 1)
        self.assertEqual(summary["minor_count"], 1)

    def test_observations_counted_by_date_code(self):
        summary = summarize_findings(
            [{"date_code": "2405", "finding_code": "marking-smear"}], REGISTER
        )
        self.assertEqual(summary["by_date_code"]["2405"]["minor"], 1)

    def test_no_observations_is_an_empty_summary(self):
        summary = summarize_findings(None, REGISTER)
        self.assertEqual(summary["critical_count"], 0)

    def test_observation_on_an_unknown_date_code_refused(self):
        with self.assertRaises(ValueError):
            summarize_findings(
                [{"date_code": "9911", "finding_code": "marking-smear"}],
                REGISTER,
                ["2338"],
            )


class VoidingTests(unittest.TestCase):
    def test_void_fraction_is_the_voided_share(self):
        self.assertAlmostEqual(die_attach_void_fraction(0.5, 4.0), 0.125, places=9)

    def test_void_over_the_die_area_refused(self):
        with self.assertRaises(ValueError):
            die_attach_void_fraction(5.0, 4.0)

    def test_zero_die_area_refused(self):
        with self.assertRaises(ValueError):
            die_attach_void_fraction(0.1, 0.0)

    def test_void_exactly_on_the_limit_is_within_it(self):
        self.assertTrue(void_within_limit(DEFAULT_VOID_LIMIT_FRACTION))

    def test_void_over_the_limit_is_outside_it(self):
        self.assertFalse(void_within_limit(0.2))

    def test_limit_above_one_refused(self):
        with self.assertRaises(ValueError):
            void_within_limit(0.05, 1.5)


class BondPullTests(unittest.TestCase):
    def test_minimum_read_from_the_register(self):
        self.assertAlmostEqual(minimum_pull_force(25), 2.5, places=9)

    def test_thicker_wire_carries_more(self):
        self.assertAlmostEqual(minimum_pull_force(50), 7.0, places=9)

    def test_unlisted_diameter_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_force(30)

    def test_register_holds_the_common_diameters(self):
        self.assertIn(25, WIRE_BOND_MINIMUM_PULL_G)
        self.assertIn(33, WIRE_BOND_MINIMUM_PULL_G)

    def test_pull_exactly_on_the_minimum_passes_with_zero_margin(self):
        out = evaluate_bond_pulls([2.5, 3.0], 25)
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(out["weakest_margin_fraction"], 0.0, places=9)

    def test_comfortable_pulls_carry_a_positive_margin(self):
        out = evaluate_bond_pulls([5.0, 6.0], 25)
        self.assertAlmostEqual(out["weakest_margin_fraction"], 1.0, places=9)

    def test_pull_under_the_minimum_fails(self):
        out = evaluate_bond_pulls([2.5, 1.8], 25)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["bonds_below_minimum"], 1)

    def test_mean_pull_reported(self):
        out = evaluate_bond_pulls([3.0, 5.0], 25)
        self.assertAlmostEqual(out["mean_pull_g"], 4.0, places=9)

    def test_empty_pull_set_refused(self):
        with self.assertRaises(ValueError):
            evaluate_bond_pulls([], 25)

    def test_non_positive_pull_refused(self):
        with self.assertRaises(ValueError):
            evaluate_bond_pulls([3.0, 0.0], 25)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "units": units(200, "2338") + units(60, "2405"),
            "finding_register": REGISTER,
            "wire_diameter_um": 25,
            "bond_pull_forces_g": [3.4, 4.1, 3.9, 5.2],
            "observations": [],
        }
        spec.update(overrides)
        return spec

    def test_clean_teardown_accepts_the_lot(self):
        out = assess_class_2_teardown(self._spec())
        self.assertEqual(out["disposition"], "lot-accepted")

    def test_sample_spans_every_date_code(self):
        out = assess_class_2_teardown(self._spec())
        self.assertEqual(out["total_sample_size"], 6)

    def test_credited_group_shrinks_the_total_sample(self):
        out = assess_class_2_teardown(
            self._spec(prior_teardown_ages={"2338": 5.0})
        )
        self.assertEqual(out["credited_groups"], ["2338"])
        self.assertEqual(out["total_sample_size"], 3)

    def test_critical_finding_rejects_the_lot(self):
        out = assess_class_2_teardown(
            self._spec(
                observations=[{"date_code": "2338", "finding_code": "cracked-die"}]
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_weak_bond_rejects_the_lot(self):
        out = assess_class_2_teardown(self._spec(bond_pull_forces_g=[3.4, 1.9]))
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_excess_voiding_rejects_the_lot(self):
        out = assess_class_2_teardown(
            self._spec(die_area_mm2=4.0, void_area_mm2=1.0)
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_voiding_on_the_limit_leaves_the_lot_accepted(self):
        out = assess_class_2_teardown(
            self._spec(die_area_mm2=4.0, void_area_mm2=0.4)
        )
        self.assertEqual(out["disposition"], "lot-accepted")
        self.assertTrue(out["die_attach_voiding"]["within_limit"])

    def test_one_void_area_without_the_other_refused(self):
        with self.assertRaises(ValueError):
            assess_class_2_teardown(self._spec(void_area_mm2=0.4))

    def test_major_finding_earns_a_second_sample_when_permitted(self):
        out = assess_class_2_teardown(
            self._spec(
                second_sample_permitted=True,
                observations=[{"date_code": "2338", "finding_code": "misaligned-die"}],
            )
        )
        self.assertEqual(out["disposition"], "second-sample-required")

    def test_second_sample_is_not_offered_twice(self):
        out = assess_class_2_teardown(
            self._spec(
                second_sample_permitted=True,
                sample_index=2,
                observations=[{"date_code": "2338", "finding_code": "misaligned-die"}],
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_critical_finding_outranks_a_permitted_second_sample(self):
        out = assess_class_2_teardown(
            self._spec(
                second_sample_permitted=True,
                observations=[{"date_code": "2405", "finding_code": "open-bond-lift"}],
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_minor_findings_over_the_allowance_reach_the_board(self):
        out = assess_class_2_teardown(
            self._spec(
                observations=[
                    {"date_code": "2338", "finding_code": "marking-smear"},
                    {"date_code": "2338", "finding_code": "surface-contamination"},
                    {"date_code": "2405", "finding_code": "marking-smear"},
                ]
            )
        )
        self.assertEqual(out["disposition"], "referred-to-parts-control-board")

    def test_minor_findings_inside_the_allowance_accept_the_lot(self):
        out = assess_class_2_teardown(
            self._spec(
                observations=[
                    {"date_code": "2338", "finding_code": "marking-smear"},
                    {"date_code": "2405", "finding_code": "marking-smear"},
                ]
            )
        )
        self.assertEqual(out["disposition"], "lot-accepted")

    def test_default_allowance_is_two(self):
        self.assertEqual(DEFAULT_MINOR_ALLOWANCE, 2)

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["wire_diameter_um"]
        with self.assertRaises(ValueError):
            assess_class_2_teardown(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_class_2_teardown(["units"])

    def test_negative_allowance_refused(self):
        with self.assertRaises(ValueError):
            assess_class_2_teardown(self._spec(minor_finding_allowance=-1))

    def test_reasons_name_the_date_code_groups(self):
        out = assess_class_2_teardown(self._spec())
        self.assertTrue(any("date-code group" in reason for reason in out["reasons"]))


if __name__ == "__main__":
    unittest.main()
