"""Contract test for the crimp rework and re-termination leaf (unittest)."""

import unittest

from q7026_rework_and_retermination_logic import (
    NO_REWORK,
    REMAKE,
    REPLACE_WIRE,
    assess_retermination,
    assess_rework_batch,
    contact_may_be_reused,
    defect_allows_rework,
    length_after_remake,
    length_budget_allows_remake,
    reterminations_remaining,
    validate_rules,
    validate_wire_end,
)


def rules(**kw):
    r = {
        "max_reterminations_per_wire_end": 3,
        "length_per_retermination_mm": 25.0,
        "required_slack_mm": 15.0,
        "reworkable_defects": [
            "bellmouth-missing",
            "insulation-support-not-formed",
            "crimp-height-out-of-window",
        ],
        "scrap_only_defects": [
            "conductor-nicked-under-the-insulation",
            "connector-housing-damaged",
        ],
        "reusable_contact_types": ["screw-clamp"],
    }
    r.update(kw)
    return r


def wire(**kw):
    w = {
        "wire_id": "W-2207",
        "contact_type": "crimp",
        "present_length_mm": 620.0,
        "routed_length_mm": 500.0,
        "reterminations_taken": 0,
    }
    w.update(kw)
    return w


class TestRuleValidation(unittest.TestCase):
    def test_a_non_mapping_rule_set_raises(self):
        with self.assertRaises(ValueError):
            validate_rules("q-st-70-26")

    def test_a_zero_retermination_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(rules(max_reterminations_per_wire_end=0))

    def test_a_zero_length_cost_per_remake_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(rules(length_per_retermination_mm=0.0))

    def test_a_negative_slack_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(rules(required_slack_mm=-5.0))

    def test_an_empty_reworkable_defect_list_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(rules(reworkable_defects=[]))

    def test_a_defect_in_both_lists_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(
                rules(scrap_only_defects=["bellmouth-missing"])
            )

    def test_declaring_a_crimp_contact_reusable_raises(self):
        with self.assertRaises(ValueError):
            validate_rules(rules(reusable_contact_types=["crimp"]))

    def test_defect_codes_are_folded_to_lower_case(self):
        checked = validate_rules(rules(reworkable_defects=["Bellmouth-Missing"]))
        self.assertIn("bellmouth-missing", checked["reworkable_defects"])


class TestWireValidation(unittest.TestCase):
    def test_a_non_mapping_wire_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(["W-2207"])

    def test_a_zero_present_length_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(wire(present_length_mm=0.0))

    def test_a_wire_already_shorter_than_its_route_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(
                wire(present_length_mm=400.0, routed_length_mm=500.0)
            )

    def test_a_negative_retermination_history_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(wire(reterminations_taken=-1))

    def test_a_non_integer_retermination_history_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(wire(reterminations_taken=1.5))

    def test_a_missing_wire_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_wire_end(wire(wire_id=""))


class TestContactReuse(unittest.TestCase):
    def test_a_crimp_contact_is_never_reusable(self):
        self.assertFalse(contact_may_be_reused("crimp", rules()))

    def test_a_declared_reusable_type_is_reusable(self):
        self.assertTrue(contact_may_be_reused("screw-clamp", rules()))

    def test_an_undeclared_type_is_treated_as_consumed(self):
        self.assertFalse(contact_may_be_reused("solder-bucket", rules()))

    def test_a_remake_on_a_crimp_contact_demands_a_new_contact(self):
        result = assess_retermination(wire(), "bellmouth-missing", rules())
        self.assertTrue(result["new_contact_required"])

    def test_a_remake_on_a_reusable_contact_does_not(self):
        result = assess_retermination(
            wire(contact_type="screw-clamp"), "bellmouth-missing", rules()
        )
        self.assertFalse(result["new_contact_required"])


class TestDefectRoute(unittest.TestCase):
    def test_a_reworkable_defect_has_a_rework_path(self):
        self.assertTrue(defect_allows_rework("bellmouth-missing", rules()))

    def test_a_scrap_only_defect_has_none(self):
        self.assertFalse(
            defect_allows_rework("connector-housing-damaged", rules())
        )

    def test_an_unlisted_defect_raises_rather_than_defaulting(self):
        with self.assertRaises(ValueError):
            defect_allows_rework("barrel-looks-a-bit-odd", rules())

    def test_a_scrap_only_defect_ends_in_no_rework(self):
        result = assess_retermination(
            wire(), "conductor-nicked-under-the-insulation", rules()
        )
        self.assertEqual(result["disposition"], NO_REWORK)
        self.assertFalse(result["permitted"])


class TestCountLimit(unittest.TestCase):
    def test_a_fresh_wire_end_has_the_full_allowance(self):
        self.assertEqual(reterminations_remaining(wire(), rules()), 3)

    def test_the_allowance_decreases_with_history(self):
        self.assertEqual(
            reterminations_remaining(wire(reterminations_taken=2), rules()), 1
        )

    def test_the_allowance_never_goes_negative(self):
        self.assertEqual(
            reterminations_remaining(wire(reterminations_taken=9), rules()), 0
        )

    def test_an_exhausted_count_sends_the_wire_for_replacement(self):
        result = assess_retermination(
            wire(reterminations_taken=3), "bellmouth-missing", rules()
        )
        self.assertEqual(result["disposition"], REPLACE_WIRE)
        self.assertIn("re-termination-count-limit-reached", result["reasons"])


class TestLengthBudget(unittest.TestCase):
    def test_the_length_after_a_remake_subtracts_the_remake_cost(self):
        self.assertAlmostEqual(
            length_after_remake(wire(), rules()), 595.0, places=9
        )

    def test_a_comfortable_wire_still_reaches(self):
        self.assertTrue(length_budget_allows_remake(wire(), rules()))

    def test_a_wire_landing_exactly_on_its_requirement_still_reaches(self):
        tight = wire(present_length_mm=540.0)
        self.assertAlmostEqual(
            length_after_remake(tight, rules()), 515.0, places=9
        )
        self.assertTrue(length_budget_allows_remake(tight, rules()))

    def test_a_wire_one_millimetre_short_does_not_reach(self):
        self.assertFalse(
            length_budget_allows_remake(wire(present_length_mm=539.0), rules())
        )

    def test_an_exhausted_length_budget_sends_the_wire_for_replacement(self):
        result = assess_retermination(
            wire(present_length_mm=530.0), "bellmouth-missing", rules()
        )
        self.assertEqual(result["disposition"], REPLACE_WIRE)
        self.assertIn(
            "wire-too-short-after-the-next-remake", result["reasons"]
        )

    def test_both_limits_are_reported_together(self):
        result = assess_retermination(
            wire(present_length_mm=530.0, reterminations_taken=3),
            "bellmouth-missing",
            rules(),
        )
        self.assertEqual(len(result["reasons"]), 2)


class TestRemakePermission(unittest.TestCase):
    def test_a_clean_case_permits_the_remake(self):
        result = assess_retermination(wire(), "crimp-height-out-of-window", rules())
        self.assertEqual(result["disposition"], REMAKE)
        self.assertTrue(result["permitted"])
        self.assertEqual(result["reasons"], [])

    def test_the_last_allowed_remake_is_still_permitted(self):
        result = assess_retermination(
            wire(reterminations_taken=2), "bellmouth-missing", rules()
        )
        self.assertEqual(result["disposition"], REMAKE)


class TestBatchRollUp(unittest.TestCase):
    def test_an_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_rework_batch([], rules())

    def test_a_non_mapping_batch_item_raises(self):
        with self.assertRaises(ValueError):
            assess_rework_batch(["W-2207"], rules())

    def test_the_batch_groups_each_route(self):
        report = assess_rework_batch(
            [
                {"wire": wire(wire_id="W-1"), "defect_code": "bellmouth-missing"},
                {
                    "wire": wire(wire_id="W-2", reterminations_taken=3),
                    "defect_code": "bellmouth-missing",
                },
                {
                    "wire": wire(wire_id="W-3"),
                    "defect_code": "connector-housing-damaged",
                },
            ],
            rules(),
        )
        self.assertEqual(report["remake"], ["W-1"])
        self.assertEqual(report["replace_wire"], ["W-2"])
        self.assertEqual(report["scrap"], ["W-3"])
        self.assertFalse(report["all_reworkable"])

    def test_the_batch_counts_the_new_contacts_needed(self):
        report = assess_rework_batch(
            [
                {"wire": wire(wire_id="W-1"), "defect_code": "bellmouth-missing"},
                {
                    "wire": wire(wire_id="W-2", contact_type="screw-clamp"),
                    "defect_code": "bellmouth-missing",
                },
            ],
            rules(),
        )
        self.assertEqual(report["new_contacts_needed"], 1)

    def test_an_all_clean_batch_is_fully_reworkable(self):
        report = assess_rework_batch(
            [{"wire": wire(), "defect_code": "bellmouth-missing"}], rules()
        )
        self.assertTrue(report["all_reworkable"])


if __name__ == "__main__":
    unittest.main()
