"""Contract tests for the clause 4.3.9 Class 1 teardown analysis logic."""

import unittest

from q60_class_1_destructive_physical_analysis_logic import (
    DEFAULT_DPA_FRACTION,
    DEFAULT_MINOR_ALLOWANCE,
    DEFECT_GRADES,
    MAXIMUM_DPA_SAMPLE,
    MINIMUM_DPA_SAMPLE,
    WIRE_BOND_MINIMUM_PULL_G,
    assess_dpa,
    dpa_sample_size,
    evaluate_bond_pulls,
    grade_defect,
    group_by_date_code,
    minimum_pull_strength,
    sampling_plan,
    summarise_defects,
)

REGISTER = {
    "cracked-die-passivation": "major",
    "voided-die-attach": "major",
    "lifted-bond": "major",
    "surface-contamination": "minor",
    "marking-smear": "minor",
}


def units(count, date_code, offset=0):
    return [
        {"serial": "%s-%04d" % (date_code, index + offset), "date_code": date_code}
        for index in range(count)
    ]


class DateCodeGroupingTests(unittest.TestCase):
    def test_single_date_code_makes_one_group(self):
        groups = group_by_date_code(units(10, "2341"))
        self.assertEqual(list(groups), ["2341"])

    def test_two_date_codes_make_two_groups(self):
        groups = group_by_date_code(units(6, "2341") + units(4, "2412"))
        self.assertEqual(sorted(groups), ["2341", "2412"])

    def test_group_sizes_are_kept_apart(self):
        groups = group_by_date_code(units(6, "2341") + units(4, "2412"))
        self.assertEqual(len(groups["2341"]), 6)
        self.assertEqual(len(groups["2412"]), 4)

    def test_date_code_is_normalised(self):
        groups = group_by_date_code(
            [{"serial": "a1", "date_code": " 2341 "}, {"serial": "a2", "date_code": "2341"}]
        )
        self.assertEqual(len(groups["2341"]), 2)

    def test_duplicate_serial_refused(self):
        with self.assertRaises(ValueError):
            group_by_date_code(
                [
                    {"serial": "a1", "date_code": "2341"},
                    {"serial": "a1", "date_code": "2412"},
                ]
            )

    def test_missing_date_code_refused(self):
        with self.assertRaises(ValueError):
            group_by_date_code([{"serial": "a1"}])

    def test_blank_date_code_refused(self):
        with self.assertRaises(ValueError):
            group_by_date_code([{"serial": "a1", "date_code": "  "}])

    def test_empty_shipment_refused(self):
        with self.assertRaises(ValueError):
            group_by_date_code([])


class SampleSizingTests(unittest.TestCase):
    def test_small_group_takes_the_minimum(self):
        self.assertEqual(dpa_sample_size(50), MINIMUM_DPA_SAMPLE)

    def test_fraction_boundary_does_not_round_up(self):
        self.assertEqual(dpa_sample_size(200), 2)

    def test_proportional_sample_above_the_minimum(self):
        self.assertEqual(dpa_sample_size(300), 3)

    def test_large_group_is_capped(self):
        self.assertEqual(dpa_sample_size(5000), MAXIMUM_DPA_SAMPLE)

    def test_group_below_the_minimum_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(1)

    def test_zero_group_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(0)

    def test_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(100, 1.5)

    def test_maximum_below_minimum_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(100, 0.01, 5, 2)

    def test_default_fraction_is_one_percent(self):
        self.assertAlmostEqual(DEFAULT_DPA_FRACTION, 0.01, places=9)


class SamplingPlanTests(unittest.TestCase):
    def test_every_group_owes_a_sample(self):
        groups = group_by_date_code(units(300, "2341") + units(60, "2412"))
        plan = sampling_plan(groups)
        self.assertEqual(sorted(plan), ["2341", "2412"])

    def test_sample_scales_with_the_group(self):
        groups = group_by_date_code(units(300, "2341") + units(60, "2412"))
        plan = sampling_plan(groups)
        self.assertEqual(plan["2341"]["sample_size"], 3)
        self.assertEqual(plan["2412"]["sample_size"], 2)

    def test_plain_counts_accepted_as_groups(self):
        plan = sampling_plan({"2341": 300})
        self.assertEqual(plan["2341"]["group_size"], 300)

    def test_flight_demand_leaves_the_spares_reported(self):
        plan = sampling_plan({"2341": 300}, {"2341": 100})
        self.assertEqual(plan["2341"]["spare_units"], 200)

    def test_demand_that_eats_the_sample_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan({"2341": 300}, {"2341": 299})

    def test_negative_demand_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan({"2341": 300}, {"2341": -1})

    def test_empty_group_map_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan({})

    def test_empty_group_refused(self):
        with self.assertRaises(ValueError):
            sampling_plan({"2341": []})


class DefectGradingTests(unittest.TestCase):
    def test_major_code_graded(self):
        self.assertEqual(grade_defect(REGISTER, "lifted-bond"), "major")

    def test_minor_code_graded(self):
        self.assertEqual(grade_defect(REGISTER, "marking-smear"), "minor")

    def test_unregistered_code_refused(self):
        with self.assertRaises(ValueError):
            grade_defect(REGISTER, "odd-looking-thing")

    def test_unknown_grade_value_refused(self):
        with self.assertRaises(ValueError):
            grade_defect({"lifted-bond": "serious"}, "lifted-bond")

    def test_grade_vocabulary_is_two_wide(self):
        self.assertEqual(DEFECT_GRADES, ("major", "minor"))

    def test_observations_counted_by_grade(self):
        summary = summarise_defects(
            [
                {"date_code": "2341", "defect_code": "lifted-bond"},
                {"date_code": "2341", "defect_code": "marking-smear"},
                {"date_code": "2412", "defect_code": "marking-smear"},
            ],
            REGISTER,
        )
        self.assertEqual(summary["major_count"], 1)
        self.assertEqual(summary["minor_count"], 2)

    def test_observations_counted_by_date_code(self):
        summary = summarise_defects(
            [
                {"date_code": "2341", "defect_code": "lifted-bond"},
                {"date_code": "2412", "defect_code": "marking-smear"},
            ],
            REGISTER,
        )
        self.assertEqual(summary["by_date_code"]["2341"]["major"], 1)
        self.assertEqual(summary["by_date_code"]["2412"]["minor"], 1)

    def test_no_observations_is_an_empty_summary(self):
        summary = summarise_defects(None, REGISTER)
        self.assertEqual(summary["major_count"], 0)
        self.assertEqual(summary["minor_count"], 0)

    def test_observation_on_an_unknown_date_code_refused(self):
        with self.assertRaises(ValueError):
            summarise_defects(
                [{"date_code": "9999", "defect_code": "marking-smear"}],
                REGISTER,
                ["2341"],
            )

    def test_observation_missing_defect_code_refused(self):
        with self.assertRaises(ValueError):
            summarise_defects([{"date_code": "2341"}], REGISTER)


class BondStrengthTests(unittest.TestCase):
    def test_minimum_read_from_the_register(self):
        self.assertAlmostEqual(minimum_pull_strength(25), 3.0, places=9)

    def test_thicker_wire_carries_more(self):
        self.assertAlmostEqual(minimum_pull_strength(50), 8.0, places=9)

    def test_unlisted_diameter_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_strength(30)

    def test_non_integer_diameter_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_strength(25.0)

    def test_register_holds_the_common_diameters(self):
        self.assertIn(25, WIRE_BOND_MINIMUM_PULL_G)
        self.assertIn(33, WIRE_BOND_MINIMUM_PULL_G)

    def test_all_pulls_above_the_minimum_pass(self):
        out = evaluate_bond_pulls([4.2, 5.1, 3.9], 25)
        self.assertTrue(out["compliant"])

    def test_pull_exactly_at_the_minimum_passes(self):
        out = evaluate_bond_pulls([3.0, 4.0, 5.0], 25)
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(out["weakest_pull"], 3.0, places=9)

    def test_pull_under_the_minimum_fails(self):
        out = evaluate_bond_pulls([2.4, 4.0, 5.0], 25)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["bonds_below_minimum"], 1)

    def test_mean_pull_reported(self):
        out = evaluate_bond_pulls([3.0, 4.0, 5.0], 25)
        self.assertAlmostEqual(out["mean_pull"], 4.0, places=9)

    def test_empty_pull_set_refused(self):
        with self.assertRaises(ValueError):
            evaluate_bond_pulls([], 25)

    def test_non_positive_pull_refused(self):
        with self.assertRaises(ValueError):
            evaluate_bond_pulls([3.0, 0.0], 25)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "units": units(300, "2341") + units(60, "2412"),
            "defect_register": REGISTER,
            "wire_diameter_um": 25,
            "bond_pull_forces_g": [4.2, 5.1, 3.9, 4.6],
            "observations": [],
        }
        spec.update(overrides)
        return spec

    def test_clean_teardown_accepts_the_lot(self):
        out = assess_dpa(self._spec())
        self.assertEqual(out["disposition"], "lot-accepted")

    def test_total_sample_spans_every_date_code(self):
        out = assess_dpa(self._spec())
        self.assertEqual(out["total_sample_size"], 5)

    def test_major_anomaly_rejects_the_lot(self):
        out = assess_dpa(
            self._spec(
                observations=[{"date_code": "2341", "defect_code": "voided-die-attach"}]
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_weak_bond_rejects_the_lot(self):
        out = assess_dpa(self._spec(bond_pull_forces_g=[4.2, 2.1, 3.9]))
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_one_minor_anomaly_is_within_the_allowance(self):
        out = assess_dpa(
            self._spec(
                observations=[{"date_code": "2341", "defect_code": "marking-smear"}]
            )
        )
        self.assertEqual(out["disposition"], "lot-accepted")

    def test_minor_anomalies_over_the_allowance_reject_by_default(self):
        out = assess_dpa(
            self._spec(
                observations=[
                    {"date_code": "2341", "defect_code": "marking-smear"},
                    {"date_code": "2412", "defect_code": "surface-contamination"},
                ]
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_second_sample_offered_when_permitted(self):
        out = assess_dpa(
            self._spec(
                second_sample_permitted=True,
                observations=[
                    {"date_code": "2341", "defect_code": "marking-smear"},
                    {"date_code": "2412", "defect_code": "surface-contamination"},
                ],
            )
        )
        self.assertEqual(out["disposition"], "second-sample-required")

    def test_second_sample_is_not_offered_twice(self):
        out = assess_dpa(
            self._spec(
                second_sample_permitted=True,
                sample_index=2,
                observations=[
                    {"date_code": "2341", "defect_code": "marking-smear"},
                    {"date_code": "2412", "defect_code": "surface-contamination"},
                ],
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_major_anomaly_outranks_a_permitted_second_sample(self):
        out = assess_dpa(
            self._spec(
                second_sample_permitted=True,
                observations=[{"date_code": "2341", "defect_code": "lifted-bond"}],
            )
        )
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_flight_demand_that_eats_the_sample_refused(self):
        with self.assertRaises(ValueError):
            assess_dpa(self._spec(flight_demand={"2412": 59}))

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["wire_diameter_um"]
        with self.assertRaises(ValueError):
            assess_dpa(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_dpa(["units"])

    def test_negative_allowance_refused(self):
        with self.assertRaises(ValueError):
            assess_dpa(self._spec(minor_defect_allowance=-1))

    def test_default_allowance_is_one(self):
        self.assertEqual(DEFAULT_MINOR_ALLOWANCE, 1)

    def test_findings_name_the_date_code_groups(self):
        out = assess_dpa(self._spec())
        self.assertTrue(any("date-code group" in f for f in out["findings"]))


if __name__ == "__main__":
    unittest.main()
