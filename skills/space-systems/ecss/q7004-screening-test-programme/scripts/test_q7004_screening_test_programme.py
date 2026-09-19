#!/usr/bin/env python3
"""Contract test for the screening test programme definition (offline)."""

import copy
import unittest

from q7004_screening_test_programme_logic import (
    CLASS_I_NOVEL,
    CLASS_II_MODIFIED,
    CLASS_III_HERITAGE,
    DEFAULT_SCREENING_POLICY,
    NO_FLIGHT_HERITAGE,
    PROCESS_CHANGE,
    SCREENING_CLASSES,
    SUPPLIER_CHANGE,
    chamber_run_count,
    define_screening_programme,
    escalate_screening_class,
    screening_cycle_count,
    screening_duration_s,
    screening_specimen_count,
    validate_screening_policy,
)

BASE_CASE = {
    "item_id": "CFRP-PANEL-A",
    "claimed_class": CLASS_II_MODIFIED,
    "flags": (),
    "cycle_duration_s": 7200.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_screening_policy(DEFAULT_SCREENING_POLICY),
            DEFAULT_SCREENING_POLICY,
        )

    def test_every_class_has_a_cycle_count_and_a_specimen_count(self):
        for item_class in SCREENING_CLASSES:
            self.assertGreaterEqual(screening_cycle_count(item_class), 1)
            self.assertGreaterEqual(screening_specimen_count(item_class), 1)

    def test_a_novel_class_screens_harder_than_a_heritage_one(self):
        self.assertGreater(
            screening_cycle_count(CLASS_I_NOVEL),
            screening_cycle_count(CLASS_III_HERITAGE),
        )

    def test_a_policy_missing_a_class_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCREENING_POLICY)
        del broken["cycles_per_class"][CLASS_II_MODIFIED]
        with self.assertRaises(ValueError):
            validate_screening_policy(broken)

    def test_a_policy_that_screens_heritage_hardest_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCREENING_POLICY)
        broken["cycles_per_class"][CLASS_III_HERITAGE] = 40
        with self.assertRaises(ValueError):
            validate_screening_policy(broken)

    def test_a_policy_below_the_cycle_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCREENING_POLICY)
        broken["cycles_per_class"][CLASS_III_HERITAGE] = 1
        with self.assertRaises(ValueError):
            validate_screening_policy(broken)

    def test_a_fractional_cycle_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCREENING_POLICY)
        broken["cycles_per_class"][CLASS_I_NOVEL] = 20.5
        with self.assertRaises(ValueError):
            validate_screening_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_screening_policy("screen everything twenty times")

    def test_an_unknown_class_has_no_cycle_count(self):
        with self.assertRaises(ValueError):
            screening_cycle_count("class-iv-legacy")


class EscalationTests(unittest.TestCase):
    def test_a_clean_claim_survives(self):
        resolution = escalate_screening_class(CLASS_III_HERITAGE, ())
        self.assertEqual(resolution["effective_class"], CLASS_III_HERITAGE)
        self.assertEqual(resolution["steps"], 0)
        self.assertEqual(resolution["reasons"], [])

    def test_one_flag_moves_the_class_one_step(self):
        resolution = escalate_screening_class(CLASS_III_HERITAGE, (PROCESS_CHANGE,))
        self.assertEqual(resolution["effective_class"], CLASS_II_MODIFIED)
        self.assertEqual(resolution["steps"], 1)

    def test_two_flags_move_the_class_two_steps(self):
        resolution = escalate_screening_class(
            CLASS_III_HERITAGE, (PROCESS_CHANGE, SUPPLIER_CHANGE)
        )
        self.assertEqual(resolution["effective_class"], CLASS_I_NOVEL)
        self.assertEqual(resolution["steps"], 2)

    def test_escalation_stops_at_the_hardest_class(self):
        resolution = escalate_screening_class(
            CLASS_II_MODIFIED,
            (PROCESS_CHANGE, SUPPLIER_CHANGE, NO_FLIGHT_HERITAGE),
        )
        self.assertEqual(resolution["effective_class"], CLASS_I_NOVEL)
        self.assertEqual(resolution["steps"], 1)

    def test_a_repeated_flag_counts_once(self):
        resolution = escalate_screening_class(
            CLASS_III_HERITAGE, (PROCESS_CHANGE, PROCESS_CHANGE)
        )
        self.assertEqual(resolution["effective_class"], CLASS_II_MODIFIED)

    def test_an_escalation_says_why(self):
        resolution = escalate_screening_class(CLASS_III_HERITAGE, (SUPPLIER_CHANGE,))
        self.assertTrue(any(SUPPLIER_CHANGE in r for r in resolution["reasons"]))

    def test_an_unknown_flag_rejected(self):
        with self.assertRaises(ValueError):
            escalate_screening_class(CLASS_III_HERITAGE, ("paint-change",))

    def test_a_non_sequence_flag_set_rejected(self):
        with self.assertRaises(ValueError):
            escalate_screening_class(CLASS_III_HERITAGE, PROCESS_CHANGE)


class RunArithmeticTests(unittest.TestCase):
    def test_a_full_load_takes_one_run(self):
        self.assertEqual(
            chamber_run_count(DEFAULT_SCREENING_POLICY["max_specimens_per_run"]), 1
        )

    def test_one_specimen_over_a_load_takes_two_runs(self):
        self.assertEqual(
            chamber_run_count(DEFAULT_SCREENING_POLICY["max_specimens_per_run"] + 1), 2
        )

    def test_a_zero_specimen_count_rejected(self):
        with self.assertRaises(ValueError):
            chamber_run_count(0)

    def test_duration_is_cycles_times_cycle_time_times_runs(self):
        self.assertAlmostEqual(
            screening_duration_s(12, 7200.0, 2), 12 * 7200.0 * 2, places=6
        )

    def test_a_second_run_doubles_the_duration(self):
        one = screening_duration_s(12, 7200.0, 1)
        two = screening_duration_s(12, 7200.0, 2)
        self.assertAlmostEqual(two / one, 2.0, places=9)

    def test_a_zero_cycle_duration_rejected(self):
        with self.assertRaises(ValueError):
            screening_duration_s(12, 0.0, 1)


class ProgrammeTests(unittest.TestCase):
    def test_the_base_programme_uses_the_class_tables(self):
        programme = define_screening_programme(BASE_CASE)
        self.assertEqual(programme["effective_class"], CLASS_II_MODIFIED)
        self.assertEqual(
            programme["cycle_count"], screening_cycle_count(CLASS_II_MODIFIED)
        )
        self.assertEqual(
            programme["specimen_count"], screening_specimen_count(CLASS_II_MODIFIED)
        )
        self.assertEqual(programme["specimen_source"], "policy")

    def test_the_programme_duration_matches_its_parts(self):
        programme = define_screening_programme(BASE_CASE)
        self.assertAlmostEqual(
            programme["programme_duration_s"],
            programme["cycle_count"]
            * programme["cycle_duration_s"]
            * programme["run_count"],
            places=6,
        )

    def test_a_flag_escalates_the_programme_and_raises_its_cycle_count(self):
        clean = define_screening_programme(
            _case(BASE_CASE, claimed_class=CLASS_III_HERITAGE)
        )
        flagged = define_screening_programme(
            _case(
                BASE_CASE, claimed_class=CLASS_III_HERITAGE, flags=(PROCESS_CHANGE,)
            )
        )
        self.assertGreater(flagged["cycle_count"], clean["cycle_count"])
        self.assertTrue(any("stand against it" in f for f in flagged["findings"]))

    def test_a_thin_declared_specimen_count_is_flagged(self):
        programme = define_screening_programme(_case(BASE_CASE, specimen_count=1))
        self.assertEqual(programme["specimen_source"], "declared")
        self.assertTrue(any("thinner" in f for f in programme["findings"]))

    def test_a_batch_beyond_the_chamber_load_needs_more_runs(self):
        programme = define_screening_programme(_case(BASE_CASE, specimen_count=17))
        self.assertEqual(programme["run_count"], 3)
        self.assertTrue(any("sequential runs" in f for f in programme["findings"]))

    def test_every_programme_states_the_screening_limit(self):
        programme = define_screening_programme(BASE_CASE)
        self.assertTrue(any("not a qualification" in d for d in programme["duties"]))

    def test_every_programme_carries_the_re_screen_duty(self):
        programme = define_screening_programme(BASE_CASE)
        self.assertTrue(any("re-screen" in d for d in programme["duties"]))

    def test_a_programme_without_a_cycle_duration_rejected(self):
        case = _case(BASE_CASE)
        del case["cycle_duration_s"]
        with self.assertRaises(ValueError):
            define_screening_programme(case)

    def test_a_blank_item_id_rejected(self):
        with self.assertRaises(ValueError):
            define_screening_programme(_case(BASE_CASE, item_id=" "))

    def test_an_unknown_claimed_class_rejected(self):
        with self.assertRaises(ValueError):
            define_screening_programme(_case(BASE_CASE, claimed_class="class-iv"))

    def test_a_fractional_specimen_count_rejected(self):
        with self.assertRaises(ValueError):
            define_screening_programme(_case(BASE_CASE, specimen_count=2.5))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            define_screening_programme("screen the panel a dozen times")


if __name__ == "__main__":
    unittest.main()
