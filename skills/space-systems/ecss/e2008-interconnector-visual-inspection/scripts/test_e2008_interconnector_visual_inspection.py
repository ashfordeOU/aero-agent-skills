#!/usr/bin/env python3
"""Contract test for the interconnector acceptance allowances (offline)."""

import copy
import unittest

from e2008_interconnector_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_INTERCONNECTOR_ALLOWANCES,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    apply_acceptance_allowances,
    assess_interconnector,
    interconnector_state,
    validate_interconnector_allowances,
)


def _interconnector(interconnector_id="IC-001", **overrides):
    record = {
        "interconnector_id": interconnector_id,
        "leg_count": 4,
        "weld_count": 8,
        "pre_test_broken_legs": 0,
        "pre_test_cracked_legs": 0,
        "pre_test_lifted_welds": 0,
        "post_test_broken_legs": 0,
        "post_test_cracked_legs": 0,
        "post_test_lifted_welds": 0,
    }
    record.update(overrides)
    return record


def _coupon(records, declared=None, coupon_id="CPN-01"):
    return {
        "coupon_id": coupon_id,
        "declared_interconnector_count": declared
        if declared is not None
        else len(records),
        "interconnectors": records,
    }


def _clean_set(how_many):
    return [_interconnector("IC-%03d" % n) for n in range(how_many)]


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_interconnector_allowances(DEFAULT_INTERCONNECTOR_ALLOWANCES),
            DEFAULT_INTERCONNECTOR_ALLOWANCES,
        )

    def test_non_mapping_allowances_rejected(self):
        with self.assertRaises(ValueError):
            validate_interconnector_allowances("default")

    def test_missing_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        del broken["max_broken_leg_fraction"]
        with self.assertRaises(ValueError):
            validate_interconnector_allowances(broken)

    def test_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        broken["max_lifted_weld_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_interconnector_allowances(broken)

    def test_zero_intact_leg_reserve_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        broken["min_intact_legs"] = 0
        with self.assertRaises(ValueError):
            validate_interconnector_allowances(broken)

    def test_broken_allowance_above_cracked_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        broken["max_broken_leg_fraction"] = 0.75
        with self.assertRaises(ValueError):
            validate_interconnector_allowances(broken)

    def test_review_margin_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        broken["review_margin_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_interconnector_allowances(broken)


class StateTests(unittest.TestCase):
    def test_clean_item_has_every_leg_intact(self):
        state = interconnector_state(_interconnector())
        self.assertEqual(state["intact_legs"], 4)
        self.assertEqual(state["induced_total"], 0)
        self.assertEqual(state["post_test_total"], 0)

    def test_induced_defects_are_the_difference_from_the_baseline(self):
        state = interconnector_state(
            _interconnector(pre_test_cracked_legs=1, post_test_cracked_legs=2)
        )
        self.assertEqual(state["induced"]["cracked_legs"], 1)
        self.assertEqual(state["induced_total"], 1)
        self.assertEqual(state["post_test_total"], 2)

    def test_a_pre_existing_defect_is_not_induced(self):
        state = interconnector_state(
            _interconnector(pre_test_broken_legs=1, post_test_broken_legs=1)
        )
        self.assertEqual(state["induced_total"], 0)
        self.assertEqual(state["intact_legs"], 3)

    def test_a_defect_that_healed_over_the_test_is_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(
                _interconnector(pre_test_broken_legs=2, post_test_broken_legs=1)
            )

    def test_more_broken_legs_than_legs_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(_interconnector(post_test_broken_legs=5))

    def test_broken_and_cracked_legs_beyond_the_leg_count_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(
                _interconnector(post_test_broken_legs=3, post_test_cracked_legs=2)
            )

    def test_more_lifted_welds_than_welds_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(_interconnector(post_test_lifted_welds=9))

    def test_zero_leg_count_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(_interconnector(leg_count=0))

    def test_non_integer_defect_count_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(_interconnector(post_test_broken_legs=1.5))

    def test_reserve_larger_than_the_leg_count_refused(self):
        with self.assertRaises(ValueError):
            interconnector_state(_interconnector(leg_count=1))

    def test_missing_interconnector_id_refused(self):
        record = _interconnector()
        del record["interconnector_id"]
        with self.assertRaises(ValueError):
            interconnector_state(record)


class ItemAllowanceTests(unittest.TestCase):
    def test_clean_item_accepts(self):
        result = assess_interconnector(_interconnector())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["defect_fractions"]["broken_legs"], 0.0, places=9)
        self.assertEqual(result["fields_over_allowance"], [])

    def test_broken_leg_exactly_on_the_allowance_accepts(self):
        result = assess_interconnector(_interconnector(post_test_broken_legs=1))
        self.assertAlmostEqual(result["defect_fractions"]["broken_legs"], 0.25, places=9)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["intact_legs"], 3)

    def test_one_leg_past_the_allowance_refers(self):
        result = assess_interconnector(_interconnector(post_test_broken_legs=2))
        self.assertEqual(result["verdict"], REFER)
        self.assertEqual(result["fields_over_allowance"], ["broken_legs"])
        self.assertEqual(result["intact_legs"], 2)

    def test_falling_below_the_intact_leg_reserve_rejects(self):
        result = assess_interconnector(_interconnector(post_test_broken_legs=3))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["intact_legs"], 1)
        self.assertTrue(any("in reserve" in f for f in result["findings"]))

    def test_a_fully_open_interconnector_rejects(self):
        result = assess_interconnector(_interconnector(post_test_broken_legs=4))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["intact_legs"], 0)
        self.assertTrue(any("open" in f for f in result["findings"]))

    def test_cracked_legs_carry_their_own_allowance(self):
        result = assess_interconnector(_interconnector(post_test_cracked_legs=3))
        self.assertEqual(result["verdict"], REFER)
        self.assertEqual(result["fields_over_allowance"], ["cracked_legs"])
        self.assertAlmostEqual(result["defect_fractions"]["cracked_legs"], 0.75, places=9)

    def test_lifted_welds_inside_the_allowance_accept(self):
        result = assess_interconnector(_interconnector(post_test_lifted_welds=1))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["defect_fractions"]["lifted_welds"], 0.125, places=9)

    def test_lifted_welds_far_past_the_allowance_reject(self):
        result = assess_interconnector(_interconnector(post_test_lifted_welds=5))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["fields_over_allowance"], ["lifted_welds"])

    def test_an_item_inside_the_allowance_still_reports_induced_damage(self):
        result = assess_interconnector(_interconnector(post_test_broken_legs=1))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["test_induced"])
        self.assertEqual(result["induced_defect_total"], 1)
        self.assertTrue(any("acceptance testing" in f for f in result["findings"]))

    def test_a_pre_existing_defect_is_not_reported_as_induced(self):
        result = assess_interconnector(
            _interconnector(pre_test_broken_legs=1, post_test_broken_legs=1)
        )
        self.assertFalse(result["test_induced"])
        self.assertEqual(result["induced_defect_total"], 0)

    def test_project_allowances_are_honoured(self):
        strict = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        strict["max_broken_leg_fraction"] = 0.20
        record = _interconnector(post_test_broken_legs=1)
        self.assertEqual(assess_interconnector(record)["verdict"], ACCEPT)
        self.assertEqual(assess_interconnector(record, strict)["verdict"], REFER)

    def test_a_zero_allowance_has_no_review_band(self):
        strict = copy.deepcopy(DEFAULT_INTERCONNECTOR_ALLOWANCES)
        strict["max_broken_leg_fraction"] = 0.0
        result = assess_interconnector(_interconnector(post_test_broken_legs=1), strict)
        self.assertEqual(result["verdict"], REJECT)


class CouponAllowanceTests(unittest.TestCase):
    def test_clean_coupon_accepts(self):
        result = apply_acceptance_allowances(_coupon(_clean_set(40)))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["affected_count"], 0)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 2.0, places=9)

    def test_affected_count_exactly_on_the_allowance_accepts(self):
        records = _clean_set(40)
        for n in range(2):
            records[n]["pre_test_broken_legs"] = 1
            records[n]["post_test_broken_legs"] = 1
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["affected_count"], 2)
        self.assertAlmostEqual(result["affected_fraction"], 0.05, places=9)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 0.0, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_one_item_past_the_coupon_allowance_refers(self):
        records = _clean_set(40)
        for n in range(3):
            records[n]["pre_test_broken_legs"] = 1
            records[n]["post_test_broken_legs"] = 1
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["verdict"], REFER)
        self.assertAlmostEqual(result["remaining_affected_allowance"], -1.0, places=9)

    def test_far_past_the_coupon_allowance_rejects(self):
        records = _clean_set(40)
        for n in range(6):
            records[n]["pre_test_broken_legs"] = 1
            records[n]["post_test_broken_legs"] = 1
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["verdict"], REJECT)

    def test_a_single_induced_defect_trips_the_coupon_induced_allowance(self):
        records = _clean_set(40)
        records[0]["post_test_lifted_welds"] = 1
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["test_induced_count"], 1)
        self.assertEqual(result["test_induced_defect_total"], 1)
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("producing them" in f for f in result["findings"]))

    def test_pre_existing_defects_do_not_trip_the_induced_allowance(self):
        records = _clean_set(40)
        for n in range(2):
            records[n]["pre_test_lifted_welds"] = 1
            records[n]["post_test_lifted_welds"] = 1
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["test_induced_count"], 0)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(
            result["remaining_test_induced_allowance"], 0.8, places=9
        )

    def test_a_rejected_item_names_itself(self):
        records = _clean_set(40)
        records[9]["pre_test_broken_legs"] = 3
        records[9]["post_test_broken_legs"] = 3
        result = apply_acceptance_allowances(_coupon(records))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["IC-009"])
        self.assertEqual(result["disposition_counts"][REJECT], 1)
        self.assertEqual(result["disposition_counts"][ACCEPT], 39)

    def test_short_record_set_leaves_the_coupon_open(self):
        result = apply_acceptance_allowances(_coupon(_clean_set(38), declared=40))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            apply_acceptance_allowances(_coupon(_clean_set(5), declared=4))

    def test_duplicate_interconnector_ids_refused(self):
        records = [_interconnector("IC-001"), _interconnector("IC-001")]
        with self.assertRaises(ValueError):
            apply_acceptance_allowances(_coupon(records))

    def test_non_integer_declared_count_refused(self):
        with self.assertRaises(ValueError):
            apply_acceptance_allowances(
                _coupon([_interconnector()], declared="forty")
            )

    def test_non_mapping_coupon_refused(self):
        with self.assertRaises(ValueError):
            apply_acceptance_allowances("CPN-01")

    def test_interconnectors_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            apply_acceptance_allowances(
                {
                    "coupon_id": "CPN-01",
                    "declared_interconnector_count": 3,
                    "interconnectors": "three",
                }
            )


if __name__ == "__main__":
    unittest.main()
