#!/usr/bin/env python3
"""Contract test for the qualification test programme definition (offline)."""

import copy
import unittest

from q7004_qualification_test_programme_logic import (
    ACCEPTANCE_MULTIPLE,
    COUPON,
    DEFAULT_QUALIFICATION_POLICY,
    EQUIPMENT,
    LEVEL_TABLE,
    SUBASSEMBLY,
    TEST_ARTICLE_LEVELS,
    level_article_count,
    level_duration_s,
    level_ladder,
    level_run_count,
    plan_qualification_programme,
    qualification_cycles,
    resolve_waivers,
    validate_qualification_policy,
)

BASE_CASE = {
    "item_id": "RW-ASSY-04",
    "highest_level": EQUIPMENT,
    "acceptance_cycles": 8,
    "cycle_duration_s": 7200.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_qualification_policy(DEFAULT_QUALIFICATION_POLICY),
            DEFAULT_QUALIFICATION_POLICY,
        )

    def test_every_level_carries_cycles_and_articles(self):
        for level in TEST_ARTICLE_LEVELS:
            self.assertGreaterEqual(level_article_count(level), 1)

    def test_a_policy_missing_a_level_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        del broken["level_cycles"][SUBASSEMBLY]
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)

    def test_a_factor_that_only_matches_acceptance_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        broken["qualification_factor"] = 1
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)

    def test_a_level_below_the_cycle_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        broken["level_cycles"][EQUIPMENT] = 5
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)

    def test_a_waivable_equipment_level_rejected(self):
        broken = copy.deepcopy(DEFAULT_QUALIFICATION_POLICY)
        broken["waivable_levels"] = (COUPON, EQUIPMENT)
        with self.assertRaises(ValueError):
            validate_qualification_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_qualification_policy("qualify on double acceptance")


class LadderTests(unittest.TestCase):
    def test_the_ladder_runs_from_the_coupon_up(self):
        self.assertEqual(level_ladder(EQUIPMENT), (COUPON, SUBASSEMBLY, EQUIPMENT))

    def test_a_coupon_programme_is_one_rung(self):
        self.assertEqual(level_ladder(COUPON), (COUPON,))

    def test_an_unknown_highest_level_rejected(self):
        with self.assertRaises(ValueError):
            level_ladder("spacecraft")

    def test_a_waivable_level_with_a_reference_is_dropped(self):
        resolution = resolve_waivers(
            level_ladder(EQUIPMENT), {COUPON: "QR-2019-114 coupon campaign"}
        )
        self.assertEqual(resolution["levels"], (SUBASSEMBLY, EQUIPMENT))
        self.assertEqual(len(resolution["waived"]), 1)

    def test_a_waiver_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            resolve_waivers(level_ladder(EQUIPMENT), {COUPON: "  "})

    def test_a_non_waivable_level_cannot_be_skipped(self):
        with self.assertRaises(ValueError):
            resolve_waivers(
                level_ladder(EQUIPMENT), {SUBASSEMBLY: "QR-2019-114"}
            )

    def test_waiving_the_whole_ladder_rejected(self):
        with self.assertRaises(ValueError):
            resolve_waivers(level_ladder(COUPON), {COUPON: "QR-2019-114"})

    def test_a_non_mapping_waiver_set_rejected(self):
        with self.assertRaises(ValueError):
            resolve_waivers(level_ladder(EQUIPMENT), [COUPON])


class CycleCountTests(unittest.TestCase):
    def test_the_level_floor_governs_a_short_acceptance_programme(self):
        result = qualification_cycles(EQUIPMENT, 8)
        self.assertEqual(result["governed_by"], LEVEL_TABLE)
        self.assertEqual(
            result["cycles"], DEFAULT_QUALIFICATION_POLICY["level_cycles"][EQUIPMENT]
        )

    def test_the_acceptance_multiple_governs_a_long_acceptance_programme(self):
        result = qualification_cycles(EQUIPMENT, 40)
        self.assertEqual(result["governed_by"], ACCEPTANCE_MULTIPLE)
        self.assertEqual(
            result["cycles"], 40 * DEFAULT_QUALIFICATION_POLICY["qualification_factor"]
        )

    def test_a_multiple_landing_on_the_floor_leaves_the_floor_governing(self):
        floor = DEFAULT_QUALIFICATION_POLICY["level_cycles"][EQUIPMENT]
        factor = DEFAULT_QUALIFICATION_POLICY["qualification_factor"]
        result = qualification_cycles(EQUIPMENT, floor // factor)
        self.assertEqual(result["cycles"], floor)
        self.assertEqual(result["governed_by"], LEVEL_TABLE)

    def test_qualification_always_exceeds_acceptance(self):
        result = qualification_cycles(EQUIPMENT, 40)
        self.assertGreater(result["cycles"], 40)

    def test_a_zero_acceptance_count_rejected(self):
        with self.assertRaises(ValueError):
            qualification_cycles(EQUIPMENT, 0)

    def test_a_fractional_acceptance_count_rejected(self):
        with self.assertRaises(ValueError):
            qualification_cycles(EQUIPMENT, 8.5)


class RunArithmeticTests(unittest.TestCase):
    def test_a_full_load_takes_one_run(self):
        self.assertEqual(
            level_run_count(DEFAULT_QUALIFICATION_POLICY["max_articles_per_run"]), 1
        )

    def test_one_article_over_a_load_takes_two_runs(self):
        self.assertEqual(
            level_run_count(DEFAULT_QUALIFICATION_POLICY["max_articles_per_run"] + 1),
            2,
        )

    def test_level_duration_is_cycles_times_cycle_time_times_runs(self):
        self.assertAlmostEqual(
            level_duration_s(50, 7200.0, 2), 50 * 7200.0 * 2, places=6
        )

    def test_a_zero_article_count_rejected(self):
        with self.assertRaises(ValueError):
            level_run_count(0)


class ProgrammeTests(unittest.TestCase):
    def test_the_base_programme_covers_the_whole_ladder(self):
        programme = plan_qualification_programme(BASE_CASE)
        self.assertEqual(programme["level_count"], 3)
        self.assertEqual(
            [entry["level"] for entry in programme["levels"]],
            [COUPON, SUBASSEMBLY, EQUIPMENT],
        )

    def test_the_programme_duration_is_the_sum_of_its_levels(self):
        programme = plan_qualification_programme(BASE_CASE)
        self.assertAlmostEqual(
            programme["programme_duration_s"],
            sum(entry["duration_s"] for entry in programme["levels"]),
            places=6,
        )

    def test_a_long_acceptance_programme_drives_the_cycle_counts_up(self):
        short = plan_qualification_programme(BASE_CASE)
        long_run = plan_qualification_programme(
            _case(BASE_CASE, acceptance_cycles=150)
        )
        self.assertGreater(
            long_run["programme_duration_s"], short["programme_duration_s"]
        )
        self.assertTrue(
            any("acceptance programme times" in f for f in long_run["findings"])
        )

    def test_a_waived_coupon_level_is_reported_with_its_reference(self):
        programme = plan_qualification_programme(
            _case(BASE_CASE, waivers={COUPON: "QR-2019-114"})
        )
        self.assertEqual(programme["level_count"], 2)
        self.assertTrue(any("QR-2019-114" in f for f in programme["findings"]))

    def test_a_coupon_only_programme_says_the_flight_item_is_unqualified(self):
        programme = plan_qualification_programme(
            _case(BASE_CASE, highest_level=COUPON)
        )
        self.assertTrue(
            any("flight configuration" in f for f in programme["findings"])
        )

    def test_a_thin_declared_article_count_is_flagged(self):
        programme = plan_qualification_programme(
            _case(BASE_CASE, articles={EQUIPMENT: 1})
        )
        entry = programme["levels"][-1]
        self.assertEqual(entry["article_source"], "declared")
        self.assertTrue(any("thinner" in f for f in programme["findings"]))

    def test_the_total_article_count_adds_the_levels_up(self):
        programme = plan_qualification_programme(BASE_CASE)
        self.assertEqual(
            programme["total_article_count"],
            sum(entry["article_count"] for entry in programme["levels"]),
        )

    def test_every_programme_keeps_the_articles_out_of_the_flight_build(self):
        programme = plan_qualification_programme(BASE_CASE)
        self.assertTrue(any("flight build" in d for d in programme["duties"]))

    def test_every_programme_carries_the_re_derivation_duty(self):
        programme = plan_qualification_programme(BASE_CASE)
        self.assertTrue(any("re-derive" in d for d in programme["duties"]))

    def test_a_declared_article_count_for_an_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification_programme(
                _case(BASE_CASE, articles={"spacecraft": 1})
            )

    def test_a_blank_item_id_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification_programme(_case(BASE_CASE, item_id=""))

    def test_a_missing_cycle_duration_rejected(self):
        case = _case(BASE_CASE)
        del case["cycle_duration_s"]
        with self.assertRaises(ValueError):
            plan_qualification_programme(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification_programme("qualify the wheel assembly")


if __name__ == "__main__":
    unittest.main()
