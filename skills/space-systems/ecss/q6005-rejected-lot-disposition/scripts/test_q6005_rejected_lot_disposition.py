#!/usr/bin/env python3
"""Gate 3 contract test for q6005-rejected-lot-disposition.

Offline, stdlib unittest. Exercises the disposition routes, their blocking
conditions, the always-open scrapping fallback, the unconditional customer
notification and the preference-ordered recommendation of ECSS-Q-ST-60-05C
clause 10.4.3 as paraphrased in the logic module. Every quantity here is a
boolean or a small integer, so the assertions compare exactly; no float bound
is asserted from a side.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_rejected_lot_disposition_logic import (  # noqa: E402
    DISPOSITION_OPTIONS,
    OPTION_OBLIGATIONS,
    customer_notification,
    eligible_dispositions,
    normalize_option,
    option_blockers,
    recommend_disposition,
    validate_context,
)


def reworkable(**overrides):
    """A refused lot whose defect can be reworked, with the customer told."""
    context = {
        "failure_mode_is_reworkable": True,
        "repair_permitted_at_assembly_stage": True,
        "remaining_repair_allowance": 1,
        "customer_notified": True,
    }
    context.update(overrides)
    return context


def downgradable(**overrides):
    """A refused lot that cannot be reworked but does meet a lower grade."""
    context = {
        "lower_grade_defined_in_specification": True,
        "customer_agreed_downgrade": True,
        "units_individually_pass_lower_grade": True,
        "customer_notified": True,
    }
    context.update(overrides)
    return context


class OptionCatalogueTests(unittest.TestCase):
    def test_every_route_carries_its_obligations(self):
        for option in DISPOSITION_OPTIONS:
            self.assertIn(option, OPTION_OBLIGATIONS)
            self.assertTrue(OPTION_OBLIGATIONS[option])

    def test_option_names_are_matched_case_and_separator_insensitively(self):
        self.assertEqual(normalize_option("  SCRAP "), "scrap")
        self.assertEqual(normalize_option("rework_and_resubmit"), "rework-and-resubmit")

    def test_unknown_route_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_option("sell-to-someone-else")

    def test_non_string_route_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_option(3)

    def test_scrapping_obliges_defacement_so_parts_cannot_return(self):
        self.assertIn(
            "physical-defacement-so-the-parts-cannot-re-enter-supply",
            OPTION_OBLIGATIONS["scrap"],
        )


class ContextValidationTests(unittest.TestCase):
    def test_a_non_mapping_context_is_refused(self):
        with self.assertRaises(ValueError):
            validate_context(["customer_notified"])

    def test_a_non_boolean_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_context({"customer_notified": "yes"})

    def test_a_non_integer_repair_allowance_is_refused(self):
        for bad in (1.5, "1", True):
            with self.assertRaises(ValueError):
                validate_context({"remaining_repair_allowance": bad})

    def test_a_negative_repair_allowance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_context({"remaining_repair_allowance": -1})

    def test_absent_flags_default_to_false(self):
        state = validate_context({})
        self.assertFalse(state["customer_notified"])
        self.assertEqual(state["remaining_repair_allowance"], 0)


class ReworkRouteTests(unittest.TestCase):
    def test_a_reworkable_defect_opens_the_rework_route(self):
        self.assertEqual(option_blockers("rework-and-resubmit", reworkable()), [])

    def test_an_unreworkable_mode_closes_the_route(self):
        blockers = option_blockers(
            "rework-and-resubmit", reworkable(failure_mode_is_reworkable=False)
        )
        self.assertTrue(any("cannot be reworked" in b for b in blockers))

    def test_an_exhausted_repair_allowance_closes_the_route(self):
        blockers = option_blockers(
            "rework-and-resubmit", reworkable(remaining_repair_allowance=0)
        )
        self.assertTrue(any("allowance" in b for b in blockers))

    def test_a_lot_wide_materials_defect_closes_the_route(self):
        blockers = option_blockers(
            "rework-and-resubmit",
            reworkable(defect_is_lot_wide_materials_or_design=True),
        )
        self.assertTrue(any("lot-wide" in b for b in blockers))

    def test_repair_not_permitted_at_the_stage_reached_closes_the_route(self):
        blockers = option_blockers(
            "rework-and-resubmit", reworkable(repair_permitted_at_assembly_stage=False)
        )
        self.assertTrue(any("assembly stage" in b for b in blockers))


class DowngradeAndWaiverTests(unittest.TestCase):
    def test_an_agreed_downgrade_that_the_units_meet_is_open(self):
        self.assertEqual(option_blockers("screen-to-lower-grade", downgradable()), [])

    def test_a_downgrade_without_customer_agreement_is_closed(self):
        blockers = option_blockers(
            "screen-to-lower-grade", downgradable(customer_agreed_downgrade=False)
        )
        self.assertTrue(any("has not agreed" in b for b in blockers))

    def test_a_defect_failing_every_grade_closes_the_downgrade(self):
        blockers = option_blockers(
            "screen-to-lower-grade", downgradable(defect_affects_every_grade=True)
        )
        self.assertTrue(any("every grade" in b for b in blockers))

    def test_a_waiver_is_closed_without_a_granted_waiver(self):
        blockers = option_blockers("use-as-is-under-waiver", {"customer_notified": True})
        self.assertTrue(any("no customer waiver" in b for b in blockers))

    def test_a_functional_failure_cannot_be_waived_even_with_a_waiver(self):
        context = {
            "customer_waiver_granted": True,
            "exceedance_is_functional_or_hermetic": True,
        }
        blockers = option_blockers("use-as-is-under-waiver", context)
        self.assertTrue(any("cannot be waived" in b for b in blockers))

    def test_return_to_manufacturer_needs_the_lot_to_still_be_theirs(self):
        self.assertEqual(
            option_blockers(
                "return-to-manufacturer", {"lot_within_manufacturer_responsibility": True}
            ),
            [],
        )
        self.assertTrue(option_blockers("return-to-manufacturer", {}))


class RecommendationTests(unittest.TestCase):
    def test_scrapping_is_open_even_when_everything_else_is_closed(self):
        routes = {r["option"]: r for r in eligible_dispositions({})}
        self.assertTrue(routes["scrap"]["eligible"])
        self.assertFalse(routes["rework-and-resubmit"]["eligible"])

    def test_rework_is_preferred_when_it_is_open(self):
        result = recommend_disposition(reworkable(**downgradable()))
        self.assertEqual(result["recommended"], "rework-and-resubmit")
        self.assertIn("re-screen-from-the-failing-stage", result["recommended_obligations"])

    def test_downgrade_is_taken_when_rework_is_closed(self):
        result = recommend_disposition(downgradable())
        self.assertEqual(result["recommended"], "screen-to-lower-grade")

    def test_a_lot_with_no_open_recovery_route_falls_to_scrap(self):
        result = recommend_disposition({"customer_notified": True})
        self.assertEqual(result["recommended"], "scrap")
        self.assertTrue(any("falls to scrapping" in f for f in result["findings"]))

    def test_notification_is_required_whatever_the_route(self):
        for context in ({}, reworkable(), downgradable()):
            self.assertTrue(customer_notification(context)["required"])

    def test_a_disposition_before_notification_is_not_admissible(self):
        result = recommend_disposition(reworkable(customer_notified=False))
        self.assertFalse(result["admissible"])
        self.assertTrue(any("not been notified" in f for f in result["findings"]))

    def test_a_notified_lot_gives_an_admissible_disposition(self):
        result = recommend_disposition(reworkable())
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_blocked_routes_are_returned_with_their_reasons(self):
        result = recommend_disposition(downgradable())
        blocked = {item["option"]: item["blockers"] for item in result["blocked_options"]}
        self.assertIn("rework-and-resubmit", blocked)
        self.assertTrue(blocked["rework-and-resubmit"])

    def test_every_route_appears_exactly_once_in_the_assessment(self):
        result = recommend_disposition(reworkable())
        names = [route["option"] for route in result["routes"]]
        self.assertEqual(names, list(DISPOSITION_OPTIONS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
