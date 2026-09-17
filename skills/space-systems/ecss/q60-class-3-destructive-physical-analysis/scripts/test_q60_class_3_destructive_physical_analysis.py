"""Contract tests for the clause 6.3.9 Class 3 teardown logic.

The cases follow a Class 3 shipment onto the teardown bench: the date codes it
splits into, the manufacturer report that can stand in for a group and the
validity that ends that, the construction baseline every torn-down piece is
compared against, the change that revokes delegation for every later build week,
the seal reading at its limit, and the lot disposition that comes out of it.

Float note: the only float comparison here is the leak rate against its limit,
and it is asserted through the module's own bound rule rather than by a strict
inequality, so the suite reads the same on any libm.
"""

import unittest

from q60_class_3_destructive_physical_analysis_logic import (
    BASELINE_ATTRIBUTES,
    CONFIRMATION_SAMPLE,
    DEFAULT_DELEGATION_VALIDITY_MONTHS,
    DEFAULT_FINE_LEAK_LIMIT,
    DEFAULT_MINOR_ALLOWANCE,
    DEFAULT_SAMPLE_FRACTION,
    DISPOSITION_PRECEDENCE,
    MAXIMUM_SAMPLE,
    MINIMUM_SAMPLE,
    OBSERVATION_CATEGORIES,
    assess_class_3_teardown,
    categorize_observation,
    compare_construction,
    date_code_week_start,
    delegation_credited,
    months_elapsed,
    partition_by_date_code,
    seal_within_limit,
    share,
    summarize_observations,
    teardown_plan,
    teardown_sample_size,
)

REGISTER = {
    "cracked-die": "critical",
    "lifted-bond": "critical",
    "voided-die-attach": "major",
    "marking-smear": "minor",
    "resin-flash": "minor",
}

BASELINE = {
    "die-marking": "MFR-A-1234",
    "passivation": "silicon-nitride",
    "metallization-system": "aluminium-copper",
    "die-attach-medium": "gold-eutectic",
    "lid-seal-method": "seam-weld",
    "wire-material": "gold",
}


def _units(count=300, date_code="2514", committed=0, prefix="A"):
    units = []
    for index in range(count):
        units.append(
            {
                "serial": "%s-%s-%04d" % (prefix, date_code, index),
                "date_code": date_code,
                "committed": index < committed,
            }
        )
    return units


def _report(date_code="2514", issued_day="2025-06-01"):
    return {"date_code": date_code, "issued_day": issued_day}


def _spec(**overrides):
    spec = {
        "units": _units(),
        "baseline": dict(BASELINE),
        "register": dict(REGISTER),
        "as_of_day": "2025-09-01",
        "reports": [],
        "observations": [],
    }
    spec.update(overrides)
    return spec


class PartitionTests(unittest.TestCase):
    def test_one_group_per_date_code(self):
        groups = partition_by_date_code(_units(10) + _units(10, "2540", prefix="B"))
        self.assertEqual(len(groups), 2)

    def test_groups_come_back_oldest_build_first(self):
        groups = partition_by_date_code(_units(5, "2540") + _units(5, "2514", prefix="B"))
        self.assertEqual([g["date_code"] for g in groups], ["2514", "2540"])

    def test_committed_pieces_leave_the_spares(self):
        groups = partition_by_date_code(_units(100, committed=40))
        self.assertEqual(groups[0]["spare"], 60)

    def test_a_repeated_serial_is_refused(self):
        units = _units(3)
        units.append(dict(units[0]))
        with self.assertRaises(ValueError):
            partition_by_date_code(units)

    def test_a_piece_without_a_date_code_is_refused(self):
        units = _units(3)
        del units[1]["date_code"]
        with self.assertRaises(ValueError):
            partition_by_date_code(units)

    def test_an_empty_shipment_is_refused(self):
        with self.assertRaises(ValueError):
            partition_by_date_code([])

    def test_a_week_a_year_does_not_have_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2553")

    def test_a_build_week_starts_on_a_monday(self):
        self.assertEqual(date_code_week_start("2514").weekday(), 0)

    def test_months_elapsed_does_not_count_a_part_month(self):
        self.assertEqual(months_elapsed("2025-01-31", "2025-02-28"), 0)


class SampleSizingTests(unittest.TestCase):
    def test_share_refuses_a_non_integer_numerator(self):
        with self.assertRaises(ValueError):
            share(1.0, 20)

    def test_share_refuses_a_zero_denominator(self):
        with self.assertRaises(ValueError):
            share(1, 0)

    def test_the_share_is_rounded_up(self):
        self.assertEqual(teardown_sample_size(301, share(1, 100)), 4)

    def test_a_small_group_is_raised_to_the_floor(self):
        self.assertEqual(teardown_sample_size(50, DEFAULT_SAMPLE_FRACTION), MINIMUM_SAMPLE)

    def test_a_large_group_is_held_under_the_cap(self):
        self.assertEqual(teardown_sample_size(100000, DEFAULT_SAMPLE_FRACTION), MAXIMUM_SAMPLE)

    def test_the_sample_never_exceeds_the_group(self):
        self.assertEqual(teardown_sample_size(1, DEFAULT_SAMPLE_FRACTION), 1)

    def test_a_share_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(300, share(5, 4))

    def test_a_cap_below_the_floor_is_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(300, DEFAULT_SAMPLE_FRACTION, minimum=6, maximum=3)

    def test_a_zero_group_is_refused(self):
        with self.assertRaises(ValueError):
            teardown_sample_size(0)


class DelegationTests(unittest.TestCase):
    def setUp(self):
        self.group = partition_by_date_code(_units(300))[0]

    def test_a_report_for_the_same_date_code_credits_the_group(self):
        verdict = delegation_credited(self.group, [_report()], "2025-09-01")
        self.assertTrue(verdict["credited"])

    def test_a_report_for_a_neighbouring_week_does_not_credit(self):
        verdict = delegation_credited(self.group, [_report("2515")], "2025-09-01")
        self.assertFalse(verdict["credited"])

    def test_a_report_past_its_validity_does_not_credit(self):
        verdict = delegation_credited(
            self.group, [_report(issued_day="2020-01-01")], "2025-09-01"
        )
        self.assertFalse(verdict["credited"])
        self.assertEqual(len(verdict["reasons"]), 1)

    def test_an_expired_report_names_the_validity_it_broke(self):
        verdict = delegation_credited(
            self.group, [_report(issued_day="2020-01-01")], "2025-09-01"
        )
        self.assertIn(str(DEFAULT_DELEGATION_VALIDITY_MONTHS), verdict["reasons"][0])

    def test_no_reports_at_all_does_not_credit(self):
        self.assertFalse(delegation_credited(self.group, [], "2025-09-01")["credited"])

    def test_a_report_without_an_issue_day_is_refused(self):
        with self.assertRaises(ValueError):
            delegation_credited(self.group, [{"date_code": "2514"}], "2025-09-01")

    def test_reports_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            delegation_credited(self.group, _report(), "2025-09-01")


class ConstructionTests(unittest.TestCase):
    def test_an_identical_build_matches_the_baseline(self):
        record = compare_construction(dict(BASELINE), dict(BASELINE))
        self.assertTrue(record["matches_baseline"])
        self.assertEqual(record["deviations"], [])

    def test_a_changed_attribute_is_a_deviation(self):
        observed = dict(BASELINE)
        observed["wire-material"] = "copper"
        record = compare_construction(observed, dict(BASELINE))
        self.assertEqual(len(record["deviations"]), 1)
        self.assertEqual(record["deviations"][0]["attribute"], "wire-material")

    def test_the_comparison_is_case_insensitive(self):
        observed = dict(BASELINE)
        observed["passivation"] = "SILICON-NITRIDE"
        self.assertTrue(compare_construction(observed, dict(BASELINE))["matches_baseline"])

    def test_every_declared_attribute_must_be_observed(self):
        observed = dict(BASELINE)
        del observed["lid-seal-method"]
        with self.assertRaises(ValueError):
            compare_construction(observed, dict(BASELINE))

    def test_an_attribute_outside_the_baseline_is_refused(self):
        observed = dict(BASELINE)
        observed["lid-colour"] = "grey"
        with self.assertRaises(ValueError):
            compare_construction(observed, dict(BASELINE))

    def test_an_incomplete_baseline_is_refused(self):
        baseline = dict(BASELINE)
        del baseline["die-marking"]
        with self.assertRaises(ValueError):
            compare_construction(dict(BASELINE), baseline)

    def test_every_baseline_attribute_is_compared(self):
        observed = {name: "changed" for name in BASELINE_ATTRIBUTES}
        record = compare_construction(observed, dict(BASELINE))
        self.assertEqual(len(record["deviations"]), len(BASELINE_ATTRIBUTES))


class ObservationTests(unittest.TestCase):
    def test_a_registered_code_returns_its_category(self):
        self.assertEqual(categorize_observation("cracked-die", REGISTER), "critical")

    def test_an_unregistered_code_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_observation("odd-looking-lid", REGISTER)

    def test_a_register_grading_outside_the_categories_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_observation("x", {"x": "cosmetic"})

    def test_an_empty_register_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_observation("cracked-die", {})

    def test_observations_are_grouped_by_category(self):
        summary = summarize_observations(
            ["marking-smear", "resin-flash", "voided-die-attach"], REGISTER
        )
        self.assertEqual(summary["counts"]["minor"], 2)
        self.assertEqual(summary["counts"]["major"], 1)

    def test_the_worst_category_present_is_reported(self):
        summary = summarize_observations(["marking-smear", "cracked-die"], REGISTER)
        self.assertEqual(summary["worst"], "critical")

    def test_a_clean_teardown_has_no_worst_category(self):
        self.assertIsNone(summarize_observations([], REGISTER)["worst"])

    def test_every_declared_category_appears_in_the_summary(self):
        summary = summarize_observations([], REGISTER)
        for category in OBSERVATION_CATEGORIES:
            self.assertIn(category, summary["counts"])


class SealTests(unittest.TestCase):
    def test_a_tight_package_passes(self):
        self.assertTrue(seal_within_limit(1e-9))

    def test_a_reading_exactly_on_the_limit_passes(self):
        self.assertTrue(seal_within_limit(DEFAULT_FINE_LEAK_LIMIT))

    def test_a_reading_clearly_above_the_limit_fails(self):
        self.assertFalse(seal_within_limit(5e-7))

    def test_a_zero_leak_reading_is_refused(self):
        with self.assertRaises(ValueError):
            seal_within_limit(0.0)

    def test_a_non_numeric_reading_is_refused(self):
        with self.assertRaises(ValueError):
            seal_within_limit("1e-9")


class PlanTests(unittest.TestCase):
    def test_a_credited_group_gives_up_a_confirmation_piece(self):
        groups = partition_by_date_code(_units(300))
        plan = teardown_plan(groups, [_report()], "2025-09-01")
        self.assertTrue(plan[0]["delegated"])
        self.assertEqual(plan[0]["sample"], CONFIRMATION_SAMPLE)

    def test_an_uncredited_group_owes_its_own_sample(self):
        groups = partition_by_date_code(_units(300))
        plan = teardown_plan(groups, [], "2025-09-01")
        self.assertFalse(plan[0]["delegated"])
        self.assertEqual(plan[0]["sample"], teardown_sample_size(300))

    def test_a_group_without_spares_is_infeasible(self):
        groups = partition_by_date_code(_units(300, committed=299))
        plan = teardown_plan(groups, [], "2025-09-01")
        self.assertFalse(plan[0]["feasible"])
        self.assertTrue(plan[0]["findings"])

    def test_a_construction_change_revokes_credit_from_that_week_on(self):
        units = _units(200, "2514") + _units(200, "2540", prefix="B")
        groups = partition_by_date_code(units)
        reports = [_report("2514"), _report("2540")]
        plan = teardown_plan(
            groups,
            reports,
            "2025-09-01",
            deviation_from_week=date_code_week_start("2540"),
        )
        self.assertTrue(plan[0]["delegated"])
        self.assertFalse(plan[1]["delegated"])

    def test_an_empty_group_list_is_refused(self):
        with self.assertRaises(ValueError):
            teardown_plan([], [], "2025-09-01")


class DispositionTests(unittest.TestCase):
    def test_a_clean_teardown_is_accepted(self):
        result = assess_class_3_teardown(_spec(observed_construction=dict(BASELINE)))
        self.assertEqual(result["disposition"], "accept")

    def test_every_disposition_is_one_of_the_declared_dispositions(self):
        result = assess_class_3_teardown(_spec())
        self.assertIn(result["disposition"], DISPOSITION_PRECEDENCE)

    def test_a_critical_observation_rejects_the_lot(self):
        result = assess_class_3_teardown(_spec(observations=["cracked-die"]))
        self.assertEqual(result["disposition"], "reject")

    def test_a_major_observation_rejects_the_lot(self):
        result = assess_class_3_teardown(_spec(observations=["voided-die-attach"]))
        self.assertEqual(result["disposition"], "reject")

    def test_a_leaking_package_rejects_the_lot(self):
        result = assess_class_3_teardown(_spec(leak_rate=5e-7))
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["seal_within_limit"])

    def test_a_construction_change_goes_to_the_parts_control_board(self):
        observed = dict(BASELINE)
        observed["die-attach-medium"] = "silver-epoxy"
        result = assess_class_3_teardown(_spec(observed_construction=observed))
        self.assertEqual(result["disposition"], "refer-to-parts-control-board")

    def test_a_critical_observation_outranks_a_construction_change(self):
        observed = dict(BASELINE)
        observed["die-attach-medium"] = "silver-epoxy"
        result = assess_class_3_teardown(
            _spec(observed_construction=observed, observations=["lifted-bond"])
        )
        self.assertEqual(result["disposition"], "reject")

    def test_cosmetic_findings_over_the_allowance_buy_a_second_sample(self):
        observations = ["marking-smear"] * (DEFAULT_MINOR_ALLOWANCE + 1)
        result = assess_class_3_teardown(_spec(observations=observations))
        self.assertEqual(result["disposition"], "second-sample")

    def test_a_second_sample_is_never_offered_twice(self):
        observations = ["marking-smear"] * (DEFAULT_MINOR_ALLOWANCE + 1)
        result = assess_class_3_teardown(
            _spec(observations=observations, sample_number=2)
        )
        self.assertEqual(result["disposition"], "reject")

    def test_a_project_that_forbids_a_second_sample_rejects_instead(self):
        observations = ["marking-smear"] * (DEFAULT_MINOR_ALLOWANCE + 1)
        result = assess_class_3_teardown(
            _spec(observations=observations, second_sample_permitted=False)
        )
        self.assertEqual(result["disposition"], "reject")

    def test_cosmetic_findings_inside_the_allowance_still_accept(self):
        observations = ["marking-smear"] * DEFAULT_MINOR_ALLOWANCE
        result = assess_class_3_teardown(_spec(observations=observations))
        self.assertEqual(result["disposition"], "accept")
        self.assertFalse(result["minor_over_allowance"])

    def test_a_construction_change_revokes_credit_inside_the_assessment(self):
        observed = dict(BASELINE)
        observed["metallization-system"] = "copper"
        units = _units(200, "2514") + _units(200, "2540", prefix="B")
        result = assess_class_3_teardown(
            _spec(
                units=units,
                reports=[_report("2514"), _report("2540")],
                observed_construction=observed,
                deviation_date_code="2540",
            )
        )
        self.assertTrue(result["plan"][0]["delegated"])
        self.assertFalse(result["plan"][1]["delegated"])

    def test_the_total_sample_sums_the_plan(self):
        result = assess_class_3_teardown(_spec())
        self.assertEqual(
            result["total_sample"], sum(e["sample"] for e in result["plan"])
        )

    def test_an_unregistered_observation_refuses_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_class_3_teardown(_spec(observations=["odd-looking-lid"]))

    def test_spec_missing_a_required_key_is_refused(self):
        spec = _spec()
        del spec["register"]
        with self.assertRaises(ValueError):
            assess_class_3_teardown(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_class_3_teardown(["units"])


if __name__ == "__main__":
    unittest.main()
