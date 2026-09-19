#!/usr/bin/env python3
"""Gate 3 contract test for q6005-repair-general-conditions.

Offline, stdlib unittest. Exercises the operator qualification, the per-
element and per-bond-site attempt allowances, the repaired-element fraction,
the repair record set and the overall permission of ECSS-Q-ST-60-05C clause
10.5.1 as paraphrased in the logic module.

The repaired-element fraction is a quotient of integers that lands exactly on
the stated limit for the populations that decide a unit, and it is not
correctly rounded to the same float on every host. That bound is asserted with
assertAlmostEqual, and the permitted side of it is read from the assessment,
which settles the equality with a named tolerance rather than a strict
comparison. Dates are supplied explicitly so the run is deterministic and
offline.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_repair_general_conditions_logic import (  # noqa: E402
    MAX_ATTEMPTS_PER_BOND_SITE,
    MAX_REPAIRED_ELEMENT_FRACTION,
    MAX_REPAIRS_PER_ELEMENT,
    REQUIRED_REPAIR_RECORDS,
    assess_repair_conditions,
    bond_site_attempts,
    element_repair_count,
    missing_records,
    operator_qualification,
    repaired_element_fraction,
    validate_repair_history,
)

REPAIR_DAY = "2026-09-18"


def operator(**overrides):
    record = {
        "identifier": "op-2741",
        "certified_actions": ["wire-rebond", "particle-removal-and-cleaning"],
        "certification_expiry": "2027-03-31",
    }
    record.update(overrides)
    return record


def proposal(**overrides):
    spec = {
        "action": "wire-rebond",
        "operator": operator(),
        "repair_date": REPAIR_DAY,
        "element": "u3",
        "total_elements": 20,
        "records_provided": list(REQUIRED_REPAIR_RECORDS),
        "prior_repairs": [],
    }
    spec.update(overrides)
    return spec


class OperatorTests(unittest.TestCase):
    def test_a_certified_unexpired_operator_is_qualified(self):
        result = operator_qualification(operator(), "wire-rebond", REPAIR_DAY)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["identifier"], "op-2741")

    def test_certification_is_per_action_not_general(self):
        result = operator_qualification(operator(), "active-die-replacement", REPAIR_DAY)
        self.assertFalse(result["qualified"])
        self.assertTrue(any("not certified" in r for r in result["reasons"]))

    def test_a_certification_lapsed_before_the_repair_does_not_cover_it(self):
        lapsed = operator(certification_expiry="2026-09-17")
        result = operator_qualification(lapsed, "wire-rebond", REPAIR_DAY)
        self.assertFalse(result["qualified"])
        self.assertTrue(any("expired" in r for r in result["reasons"]))

    def test_a_certification_expiring_on_the_day_still_covers_it(self):
        same_day = operator(certification_expiry=REPAIR_DAY)
        self.assertTrue(operator_qualification(same_day, "wire-rebond", REPAIR_DAY)["qualified"])

    def test_a_certification_with_no_expiry_is_not_accepted_as_open_ended(self):
        never = operator()
        del never["certification_expiry"]
        result = operator_qualification(never, "wire-rebond", REPAIR_DAY)
        self.assertFalse(result["qualified"])
        self.assertTrue(any("no expiry" in r for r in result["reasons"]))

    def test_an_anonymous_operator_is_refused(self):
        for bad in ({"identifier": "  "}, {"identifier": None}, {}):
            with self.assertRaises(ValueError):
                operator_qualification(bad, "wire-rebond", REPAIR_DAY)

    def test_a_malformed_repair_date_is_refused(self):
        with self.assertRaises(ValueError):
            operator_qualification(operator(), "wire-rebond", "18-09-2026")

    def test_certified_actions_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            operator_qualification(operator(certified_actions="wire-rebond"), "wire-rebond", REPAIR_DAY)


class HistoryTests(unittest.TestCase):
    def test_history_must_be_a_sequence_of_records(self):
        with self.assertRaises(ValueError):
            validate_repair_history({"element": "u3"})

    def test_a_history_record_without_an_element_is_refused(self):
        with self.assertRaises(ValueError):
            validate_repair_history([{"bond_site": "u3-b1"}])

    def test_element_names_are_matched_case_and_separator_insensitively(self):
        history = [{"element": "U 3"}, {"element": "u-3"}]
        self.assertEqual(element_repair_count(history, "u3"), 0)
        self.assertEqual(element_repair_count(history, "u-3"), 2)

    def test_bond_site_attempts_count_the_original_bond(self):
        self.assertEqual(bond_site_attempts([], "u3-b1"), 1)
        self.assertEqual(bond_site_attempts([{"element": "u3", "bond_site": "u3-b1"}], "u3-b1"), 2)

    def test_an_absent_bond_site_spends_no_attempt(self):
        self.assertEqual(bond_site_attempts([{"element": "u3"}], None), 0)


class FractionTests(unittest.TestCase):
    def test_a_first_repair_on_a_large_unit_is_a_small_fraction(self):
        self.assertAlmostEqual(repaired_element_fraction([], "u3", 50), 0.02, places=9)

    def test_the_fraction_counts_distinct_elements_not_repair_events(self):
        history = [{"element": "u3", "bond_site": "u3-b1"}, {"element": "u3"}]
        self.assertAlmostEqual(repaired_element_fraction(history, "u3", 20), 0.05, places=9)

    def test_the_fraction_can_land_exactly_on_the_limit(self):
        history = [{"element": "u%d" % i} for i in range(1, 3)]
        fraction = repaired_element_fraction(history, "u9", 30)
        self.assertAlmostEqual(fraction, MAX_REPAIRED_ELEMENT_FRACTION, places=9)

    def test_a_non_positive_element_count_is_refused(self):
        for bad in (0, -4, 2.5, "20", True):
            with self.assertRaises(ValueError):
                repaired_element_fraction([], "u3", bad)

    def test_more_repaired_elements_than_the_unit_holds_is_refused(self):
        history = [{"element": "u1"}, {"element": "u2"}]
        with self.assertRaises(ValueError):
            repaired_element_fraction(history, "u3", 2)


class RecordTests(unittest.TestCase):
    def test_a_complete_record_set_leaves_nothing_missing(self):
        self.assertEqual(missing_records(list(REQUIRED_REPAIR_RECORDS)), [])

    def test_record_names_are_matched_case_and_separator_insensitively(self):
        provided = [name.replace("-", " ").upper() for name in REQUIRED_REPAIR_RECORDS]
        self.assertEqual(missing_records(provided), [])

    def test_an_absent_record_is_reported(self):
        provided = [name for name in REQUIRED_REPAIR_RECORDS if name != "rescreen-record"]
        self.assertEqual(missing_records(provided), ["rescreen-record"])

    def test_a_string_is_not_a_record_list(self):
        with self.assertRaises(ValueError):
            missing_records("repair-authorization")


class AssessmentTests(unittest.TestCase):
    def test_a_qualified_first_repair_with_full_records_is_permitted(self):
        result = assess_repair_conditions(proposal())
        self.assertTrue(result["permitted"])
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["operator_qualified"])

    def test_an_uncertified_operator_blocks_the_repair(self):
        spec = proposal(action="active-die-replacement")
        result = assess_repair_conditions(spec)
        self.assertFalse(result["permitted"])
        self.assertFalse(result["operator_qualified"])

    def test_a_second_repair_on_the_same_element_is_blocked(self):
        spec = proposal(prior_repairs=[{"element": "u3"}])
        result = assess_repair_conditions(spec)
        self.assertFalse(result["permitted"])
        self.assertEqual(result["element_prior_repairs"], MAX_REPAIRS_PER_ELEMENT)
        self.assertTrue(any("allowance is 1" in b for b in result["blockers"]))

    def test_a_third_attempt_at_one_bond_site_is_blocked(self):
        history = [
            {"element": "u4", "bond_site": "u3-b1"},
            {"element": "u5", "bond_site": "u3-b1"},
        ]
        spec = proposal(bond_site="u3-b1", prior_repairs=history, total_elements=60)
        result = assess_repair_conditions(spec)
        self.assertEqual(result["bond_site_attempt"], MAX_ATTEMPTS_PER_BOND_SITE + 1)
        self.assertFalse(result["permitted"])

    def test_the_last_permitted_bond_attempt_is_allowed_and_flagged(self):
        spec = proposal(
            bond_site="u3-b1",
            prior_repairs=[{"element": "u4", "bond_site": "u3-b1"}],
            total_elements=60,
        )
        result = assess_repair_conditions(spec)
        self.assertTrue(result["permitted"])
        self.assertEqual(result["bond_site_attempt"], MAX_ATTEMPTS_PER_BOND_SITE)
        self.assertTrue(any("last permitted attempt" in f for f in result["findings"]))

    def test_a_unit_exactly_on_the_repaired_fraction_limit_is_still_permitted(self):
        history = [{"element": "u1"}, {"element": "u2"}]
        spec = proposal(element="u9", total_elements=30, prior_repairs=history)
        result = assess_repair_conditions(spec)
        self.assertAlmostEqual(
            result["repaired_element_fraction"], MAX_REPAIRED_ELEMENT_FRACTION, places=9
        )
        self.assertTrue(result["permitted"])
        self.assertTrue(any("on its repaired-element limit" in f for f in result["findings"]))

    def test_a_unit_past_the_repaired_fraction_limit_is_blocked(self):
        history = [{"element": "u%d" % i} for i in range(1, 4)]
        spec = proposal(element="u9", total_elements=30, prior_repairs=history)
        result = assess_repair_conditions(spec)
        self.assertFalse(result["permitted"])
        self.assertTrue(any("limit is" in b for b in result["blockers"]))

    def test_an_incomplete_record_set_blocks_the_repair(self):
        spec = proposal(records_provided=["repair-authorization", "operator-identity"])
        result = assess_repair_conditions(spec)
        self.assertFalse(result["permitted"])
        self.assertTrue(any("record set incomplete" in b for b in result["blockers"]))

    def test_every_failing_condition_is_named_not_just_the_first(self):
        spec = proposal(
            action="active-die-replacement",
            prior_repairs=[{"element": "u3"}],
            records_provided=["repair-authorization"],
        )
        result = assess_repair_conditions(spec)
        self.assertGreaterEqual(len(result["blockers"]), 3)

    def test_missing_required_key_is_refused(self):
        for key in ("action", "operator", "repair_date", "element", "total_elements",
                    "records_provided"):
            spec = proposal()
            del spec[key]
            with self.assertRaises(ValueError):
                assess_repair_conditions(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_repair_conditions(["wire-rebond"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
