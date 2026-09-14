#!/usr/bin/env python3
"""Contract test for the Class 3 baseline selection rules (offline)."""

import copy
import unittest

from q6013_class_3_selection_rules_logic import (
    PART_ADMISSIBLE,
    PART_ADMISSIBLE_WITH_ACTIONS,
    PART_NOT_ADMISSIBLE,
    PRODUCTION_STATUSES,
    QUALITY_SYSTEMS,
    RULE_BREACHED,
    RULE_CONDITIONAL,
    RULE_MET,
    RULE_ORDER,
    TRACEABILITY_LEVELS,
    apply_selection_rules,
    assess_production_status,
    assess_qualified_alternative,
    assess_quality_system,
    assess_temperature_rule,
    assess_traceability,
    temperature_margins,
)

GOOD_CANDIDATE = {
    "rated_min_c": -40.0,
    "rated_max_c": 105.0,
    "production_status": "serial-production",
    "lifetime_buy_secured": False,
    "quality_system": "certified-quality-system",
    "traceability": "lot-and-date-code",
    "single_lot_delivery": True,
    "alternative_available": False,
    "alternative_fits_slot": False,
}

GOOD_ENVELOPE = {
    "min_temperature_c": -20.0,
    "max_temperature_c": 70.0,
    "required_margin_c": 10.0,
}


def _candidate(**overrides):
    case = copy.deepcopy(GOOD_CANDIDATE)
    case.update(overrides)
    return case


def _envelope(**overrides):
    case = copy.deepcopy(GOOD_ENVELOPE)
    case.update(overrides)
    return case


class TemperatureRuleTests(unittest.TestCase):
    def test_margins_are_the_two_differences(self):
        margins = temperature_margins(-40.0, 105.0, -20.0, 70.0)
        self.assertAlmostEqual(margins["cold_margin_c"], 20.0, places=9)
        self.assertAlmostEqual(margins["hot_margin_c"], 35.0, places=9)

    def test_range_with_room_at_both_ends_is_met(self):
        graded = assess_temperature_rule(-40.0, 105.0, -20.0, 70.0, 10.0)
        self.assertEqual(graded["verdict"], RULE_MET)
        self.assertEqual(graded["tightest_end"], "cold")

    def test_margin_exactly_on_the_requirement_is_met(self):
        graded = assess_temperature_rule(-40.0, 105.0, -30.0, 70.0, 10.0)
        self.assertEqual(graded["verdict"], RULE_MET)
        self.assertAlmostEqual(graded["tightest_margin_c"], 10.0, places=9)

    def test_coverage_without_the_declared_margin_is_conditional(self):
        graded = assess_temperature_rule(-40.0, 105.0, -35.0, 70.0, 10.0)
        self.assertEqual(graded["verdict"], RULE_CONDITIONAL)

    def test_mission_outside_the_rating_is_breached(self):
        graded = assess_temperature_rule(-40.0, 105.0, -55.0, 70.0, 0.0)
        self.assertEqual(graded["verdict"], RULE_BREACHED)
        self.assertLess(graded["tightest_margin_c"], -1.0)

    def test_hot_end_can_be_the_tightest(self):
        graded = assess_temperature_rule(-60.0, 85.0, -20.0, 80.0, 0.0)
        self.assertEqual(graded["tightest_end"], "hot")
        self.assertAlmostEqual(graded["tightest_margin_c"], 5.0, places=9)

    def test_inverted_rating_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins(105.0, -40.0, -20.0, 70.0)

    def test_inverted_envelope_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins(-40.0, 105.0, 70.0, -20.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins(-400.0, 105.0, -20.0, 70.0)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins("cold", 105.0, -20.0, 70.0)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_rule(-40.0, 105.0, -20.0, 70.0, -5.0)


class ProductionStatusTests(unittest.TestCase):
    def test_serial_production_is_met(self):
        self.assertEqual(
            assess_production_status("serial-production")["verdict"], RULE_MET
        )

    def test_announced_obsolete_with_a_lifetime_buy_is_conditional(self):
        graded = assess_production_status("announced-obsolete", True)
        self.assertEqual(graded["verdict"], RULE_CONDITIONAL)

    def test_announced_obsolete_without_a_lifetime_buy_is_breached(self):
        graded = assess_production_status("announced-obsolete", False)
        self.assertEqual(graded["verdict"], RULE_BREACHED)

    def test_withdrawn_part_is_breached_even_with_a_lifetime_buy(self):
        graded = assess_production_status("end-of-life", True)
        self.assertEqual(graded["verdict"], RULE_BREACHED)

    def test_sample_build_part_is_breached(self):
        graded = assess_production_status("prototype-sample")
        self.assertEqual(graded["verdict"], RULE_BREACHED)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_status("rumoured")

    def test_non_boolean_lifetime_buy_rejected(self):
        with self.assertRaises(ValueError):
            assess_production_status("announced-obsolete", "yes")

    def test_every_status_is_graded(self):
        for status in PRODUCTION_STATUSES:
            graded = assess_production_status(status, True)
            self.assertIn(graded["verdict"], (RULE_MET, RULE_CONDITIONAL, RULE_BREACHED))


class QualitySystemTests(unittest.TestCase):
    def test_certified_system_is_met(self):
        self.assertEqual(
            assess_quality_system("certified-quality-system")["verdict"], RULE_MET
        )

    def test_project_audit_is_met(self):
        self.assertEqual(assess_quality_system("project-audited")["verdict"], RULE_MET)

    def test_unverified_declaration_is_conditional(self):
        self.assertEqual(
            assess_quality_system("declared-not-verified")["verdict"], RULE_CONDITIONAL
        )

    def test_absent_system_is_breached(self):
        self.assertEqual(assess_quality_system("none")["verdict"], RULE_BREACHED)

    def test_unknown_system_rejected(self):
        with self.assertRaises(ValueError):
            assess_quality_system("probably-fine")

    def test_every_system_is_graded(self):
        for system in QUALITY_SYSTEMS:
            self.assertIn(
                assess_quality_system(system)["verdict"],
                (RULE_MET, RULE_CONDITIONAL, RULE_BREACHED),
            )


class TraceabilityTests(unittest.TestCase):
    def test_single_lot_with_full_identity_is_met(self):
        self.assertEqual(
            assess_traceability("lot-and-date-code", True)["verdict"], RULE_MET
        )

    def test_mixed_lots_are_conditional(self):
        self.assertEqual(
            assess_traceability("lot-and-date-code", False)["verdict"], RULE_CONDITIONAL
        )

    def test_date_code_alone_is_conditional(self):
        self.assertEqual(
            assess_traceability("date-code-only", True)["verdict"], RULE_CONDITIONAL
        )

    def test_no_identity_is_breached(self):
        self.assertEqual(assess_traceability("none", True)["verdict"], RULE_BREACHED)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability("serial-number-maybe")

    def test_every_level_is_graded(self):
        for level in TRACEABILITY_LEVELS:
            self.assertIn(
                assess_traceability(level, True)["verdict"],
                (RULE_MET, RULE_CONDITIONAL, RULE_BREACHED),
            )


class QualifiedAlternativeTests(unittest.TestCase):
    def test_no_alternative_is_met(self):
        self.assertEqual(
            assess_qualified_alternative(False, False)["verdict"], RULE_MET
        )

    def test_fitting_alternative_is_breached(self):
        self.assertEqual(
            assess_qualified_alternative(True, True)["verdict"], RULE_BREACHED
        )

    def test_alternative_that_does_not_fit_is_conditional(self):
        self.assertEqual(
            assess_qualified_alternative(True, False)["verdict"], RULE_CONDITIONAL
        )

    def test_non_boolean_availability_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualified_alternative("maybe", False)


class ApplySelectionRulesTests(unittest.TestCase):
    def test_clean_candidate_is_admissible(self):
        result = apply_selection_rules(GOOD_CANDIDATE, GOOD_ENVELOPE)
        self.assertEqual(result["verdict"], PART_ADMISSIBLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["open_actions"], [])

    def test_every_rule_is_graded_once(self):
        result = apply_selection_rules(GOOD_CANDIDATE, GOOD_ENVELOPE)
        self.assertEqual(
            tuple(entry["rule"] for entry in result["rules"]), RULE_ORDER
        )

    def test_one_conditional_rule_makes_it_admissible_with_actions(self):
        result = apply_selection_rules(
            _candidate(traceability="date-code-only"), GOOD_ENVELOPE
        )
        self.assertEqual(result["verdict"], PART_ADMISSIBLE_WITH_ACTIONS)
        self.assertTrue(result["admissible"])
        self.assertEqual(len(result["open_actions"]), 1)

    def test_one_breached_rule_makes_it_not_admissible(self):
        result = apply_selection_rules(
            _candidate(quality_system="none"), GOOD_ENVELOPE
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertFalse(result["admissible"])

    def test_binding_rule_is_the_worst_one(self):
        result = apply_selection_rules(
            _candidate(traceability="date-code-only", production_status="end-of-life"),
            GOOD_ENVELOPE,
        )
        self.assertEqual(result["binding_rule"], "production-status")

    def test_binding_rule_breaks_a_tie_in_declared_order(self):
        result = apply_selection_rules(
            _candidate(quality_system="none", traceability="none"), GOOD_ENVELOPE
        )
        self.assertEqual(result["binding_rule"], "manufacturer-quality-system")

    def test_a_fitting_qualified_alternative_blocks_the_commercial_route(self):
        result = apply_selection_rules(
            _candidate(alternative_available=True, alternative_fits_slot=True),
            GOOD_ENVELOPE,
        )
        self.assertEqual(result["verdict"], PART_NOT_ADMISSIBLE)
        self.assertEqual(result["binding_rule"], "qualified-alternative")

    def test_every_open_rule_carries_an_action(self):
        result = apply_selection_rules(
            _candidate(traceability="none", quality_system="declared-not-verified"),
            GOOD_ENVELOPE,
        )
        rules_open = {entry["rule"] for entry in result["rules"] if entry["verdict"] != RULE_MET}
        self.assertEqual({a["rule"] for a in result["open_actions"]}, rules_open)
        for action in result["open_actions"]:
            self.assertTrue(action["action"])

    def test_margin_sitting_exactly_on_the_requirement_stays_admissible(self):
        result = apply_selection_rules(
            GOOD_CANDIDATE, _envelope(min_temperature_c=-30.0, required_margin_c=10.0)
        )
        self.assertEqual(result["verdict"], PART_ADMISSIBLE)

    def test_missing_rating_rejected(self):
        candidate = _candidate()
        del candidate["rated_max_c"]
        with self.assertRaises(ValueError):
            apply_selection_rules(candidate, GOOD_ENVELOPE)

    def test_missing_envelope_bound_rejected(self):
        envelope = _envelope()
        del envelope["max_temperature_c"]
        with self.assertRaises(ValueError):
            apply_selection_rules(GOOD_CANDIDATE, envelope)

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            apply_selection_rules(["a-part"], GOOD_ENVELOPE)

    def test_non_mapping_envelope_rejected(self):
        with self.assertRaises(ValueError):
            apply_selection_rules(GOOD_CANDIDATE, "-20 to 70")

    def test_absent_status_rejected_rather_than_defaulted(self):
        candidate = _candidate()
        del candidate["production_status"]
        with self.assertRaises(ValueError):
            apply_selection_rules(candidate, GOOD_ENVELOPE)

    def test_by_rule_index_matches_the_graded_list(self):
        result = apply_selection_rules(GOOD_CANDIDATE, GOOD_ENVELOPE)
        for entry in result["rules"]:
            self.assertIs(result["by_rule"][entry["rule"]], entry)


if __name__ == "__main__":
    unittest.main(verbosity=1)
