#!/usr/bin/env python3
"""Contract test for the Class 2 radiation hardness selection leaf (offline)."""

import copy
import unittest

from q60_class_2_radiation_hardness_selection_logic import (
    DEFAULT_MARGIN_BY_PEDIGREE,
    DEFAULT_SHIELDING_UPLIFT_LIMIT,
    EVIDENCE_PEDIGREES,
    LOT_SPECIFIC_PEDIGREE,
    MECHANISM_DISPLACEMENT,
    MECHANISM_TOTAL_DOSE,
    RAD_ACCEPTED,
    RAD_INCOMPLETE,
    RAD_LOT_TEST,
    RAD_MITIGATION,
    RAD_REFUSED,
    RAD_SHIELDING,
    accumulate_mission_environment,
    assess_part,
    grade_accumulated_mechanism,
    grade_single_event,
    radiation_design_margin,
    supported_lifetime_months,
    validate_margin_policy,
    validate_mission_profile,
)

PHASES = [
    {
        "phase": "transfer-orbit",
        "duration_months": 3.0,
        "shielded_dose_rate_krad_per_month": 2.0,
        "shielded_fluence_rate_per_month": 1.0e10,
    },
    {
        "phase": "operational-orbit",
        "duration_months": 57.0,
        "shielded_dose_rate_krad_per_month": 0.5,
        "shielded_fluence_rate_per_month": 2.0e9,
    },
]

ENVIRONMENT = {
    "environment_let_mev_cm2_mg": 60.0,
    "upset_rate_budget_per_day": 2.0,
}

PART = {
    "part_reference": "u-3001",
    "evidence_pedigree": "same-diffusion-lot-data",
    "rated_total_dose_krad": 100.0,
    "rated_displacement_fluence": 5.0e11,
    "destructive_event_let_threshold": 80.0,
    "mitigated_upset_rate_per_day": 0.5,
}


def _part(**overrides):
    item = copy.deepcopy(PART)
    item.update(overrides)
    return item


def _environment(**overrides):
    item = copy.deepcopy(ENVIRONMENT)
    item.update(overrides)
    return item


class MarginPolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_margin_policy({})
        self.assertEqual(
            settings["margin_by_pedigree"], DEFAULT_MARGIN_BY_PEDIGREE
        )
        self.assertAlmostEqual(
            settings["shielding_uplift_limit"],
            DEFAULT_SHIELDING_UPLIFT_LIMIT,
            places=9,
        )

    def test_a_lot_measurement_costs_the_smallest_margin(self):
        lot = radiation_design_margin(LOT_SPECIFIC_PEDIGREE)
        for pedigree in EVIDENCE_PEDIGREES:
            margin = radiation_design_margin(pedigree)
            if pedigree == LOT_SPECIFIC_PEDIGREE:
                # The same policy entry read twice: the same float, so the
                # closed end of the ordering is an equality, not a bound.
                self.assertEqual(lot, margin)
            else:
                self.assertLess(lot, margin)

    def test_a_datasheet_claim_costs_the_largest_margin(self):
        claim = radiation_design_margin("manufacturer-datasheet-claim")
        for pedigree in EVIDENCE_PEDIGREES:
            margin = radiation_design_margin(pedigree)
            if pedigree == "manufacturer-datasheet-claim":
                # The same policy entry read twice: the same float, so the
                # closed end of the ordering is an equality, not a bound.
                self.assertEqual(claim, margin)
            else:
                self.assertGreater(claim, margin)

    def test_no_margin_sits_below_unity(self):
        for pedigree in EVIDENCE_PEDIGREES:
            self.assertGreaterEqual(radiation_design_margin(pedigree), 1.0)

    def test_unknown_pedigree_rejected(self):
        with self.assertRaises(ValueError):
            radiation_design_margin("someone-said-it-was-fine")

    def test_policy_missing_a_pedigree_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_BY_PEDIGREE)
        del broken["generic-part-family-data"]
        with self.assertRaises(ValueError):
            validate_margin_policy({"margin_by_pedigree": broken})

    def test_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_BY_PEDIGREE)
        broken[LOT_SPECIFIC_PEDIGREE] = 0.8
        with self.assertRaises(ValueError):
            validate_margin_policy({"margin_by_pedigree": broken})

    def test_shielding_uplift_limit_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_policy({"shielding_uplift_limit": 0.5})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_policy("default")


class MissionProfileTests(unittest.TestCase):
    def test_profile_totals_the_declared_months(self):
        result = accumulate_mission_environment(PHASES)
        self.assertAlmostEqual(result["total_months"], 60.0, places=9)

    def test_dose_accumulates_phase_by_phase(self):
        result = accumulate_mission_environment(PHASES)
        self.assertAlmostEqual(result["total_dose_krad"], 34.5, places=9)

    def test_fluence_accumulates_phase_by_phase(self):
        result = accumulate_mission_environment(PHASES)
        self.assertAlmostEqual(result["total_fluence"], 1.44e11, delta=1.0e3)

    def test_the_walk_reports_a_running_total_per_phase(self):
        result = accumulate_mission_environment(PHASES)
        self.assertEqual(len(result["per_phase"]), 2)
        self.assertAlmostEqual(
            result["per_phase"][0]["cumulative_dose_krad"], 6.0, places=9
        )

    def test_a_phase_with_no_duration_rejected(self):
        broken = copy.deepcopy(PHASES)
        broken[0]["duration_months"] = 0.0
        with self.assertRaises(ValueError):
            validate_mission_profile(broken)

    def test_a_negative_dose_rate_rejected(self):
        broken = copy.deepcopy(PHASES)
        broken[0]["shielded_dose_rate_krad_per_month"] = -1.0
        with self.assertRaises(ValueError):
            validate_mission_profile(broken)

    def test_a_repeated_phase_name_rejected(self):
        broken = copy.deepcopy(PHASES) + [copy.deepcopy(PHASES[0])]
        with self.assertRaises(ValueError):
            validate_mission_profile(broken)

    def test_an_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_profile([])

    def test_an_unnamed_phase_rejected(self):
        broken = copy.deepcopy(PHASES)
        broken[1]["phase"] = " "
        with self.assertRaises(ValueError):
            validate_mission_profile(broken)


class AccumulatedMechanismTests(unittest.TestCase):
    def test_margin_raises_the_requirement(self):
        result = grade_accumulated_mechanism(
            MECHANISM_TOTAL_DOSE, 34.5, 100.0, 1.5
        )
        self.assertAlmostEqual(result["required_capability"], 51.75, places=9)
        self.assertTrue(result["covered"])

    def test_a_requirement_exactly_on_the_capability_is_covered(self):
        result = grade_accumulated_mechanism(
            MECHANISM_TOTAL_DOSE, 34.5, 51.75, 1.5
        )
        self.assertAlmostEqual(
            result["required_capability"], result["declared_capability"], places=9
        )
        self.assertTrue(result["covered"])

    def test_a_requirement_past_the_capability_is_not_covered(self):
        result = grade_accumulated_mechanism(
            MECHANISM_TOTAL_DOSE, 34.5, 40.0, 1.5
        )
        self.assertFalse(result["covered"])

    def test_utilisation_is_reported(self):
        result = grade_accumulated_mechanism(
            MECHANISM_TOTAL_DOSE, 20.0, 100.0, 2.0
        )
        self.assertAlmostEqual(result["utilisation"], 0.4, places=9)

    def test_a_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            grade_accumulated_mechanism(MECHANISM_TOTAL_DOSE, 34.5, 0.0, 1.5)

    def test_a_negative_accumulation_rejected(self):
        with self.assertRaises(ValueError):
            grade_accumulated_mechanism(MECHANISM_TOTAL_DOSE, -1.0, 100.0, 1.5)


class SingleEventTests(unittest.TestCase):
    def test_a_threshold_above_the_environment_is_immune(self):
        result = grade_single_event(PART, ENVIRONMENT)
        self.assertTrue(result["destructive"]["immune"])

    def test_a_threshold_on_the_environment_takes_no_rate_credit(self):
        part = _part(destructive_event_let_threshold=60.0)
        result = grade_single_event(part, ENVIRONMENT)
        self.assertAlmostEqual(
            result["destructive"]["threshold_let"],
            result["destructive"]["environment_let"],
            places=9,
        )
        self.assertFalse(result["destructive"]["immune"])

    def test_a_threshold_below_the_environment_is_not_immune(self):
        part = _part(destructive_event_let_threshold=40.0)
        result = grade_single_event(part, ENVIRONMENT)
        self.assertFalse(result["destructive"]["immune"])

    def test_a_missing_destructive_threshold_leaves_the_mechanism_open(self):
        part = _part()
        del part["destructive_event_let_threshold"]
        result = grade_single_event(part, ENVIRONMENT)
        self.assertIsNone(result["destructive"])
        self.assertTrue(result["findings"])

    def test_an_upset_rate_inside_the_budget_passes(self):
        result = grade_single_event(PART, ENVIRONMENT)
        self.assertTrue(result["recoverable"]["within_budget"])

    def test_an_upset_rate_exactly_on_the_budget_passes(self):
        part = _part(mitigated_upset_rate_per_day=2.0)
        result = grade_single_event(part, ENVIRONMENT)
        self.assertAlmostEqual(
            result["recoverable"]["mitigated_rate_per_day"],
            result["recoverable"]["budget_per_day"],
            places=9,
        )
        self.assertTrue(result["recoverable"]["within_budget"])

    def test_an_upset_rate_over_the_budget_fails(self):
        part = _part(mitigated_upset_rate_per_day=5.0)
        result = grade_single_event(part, ENVIRONMENT)
        self.assertFalse(result["recoverable"]["within_budget"])

    def test_a_missing_budget_leaves_the_rate_ungraded(self):
        environment = _environment()
        del environment["upset_rate_budget_per_day"]
        result = grade_single_event(PART, environment)
        self.assertIsNone(result["recoverable"])

    def test_a_zero_environment_let_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(PART, _environment(environment_let_mev_cm2_mg=0.0))

    def test_non_mapping_environment_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(PART, "geostationary")


class LifetimeTests(unittest.TestCase):
    def test_a_capable_part_covers_the_whole_declared_mission(self):
        result = supported_lifetime_months(PART, PHASES)
        self.assertAlmostEqual(result["supported_months"], 60.0, places=9)
        self.assertIsNone(result["exhausted_in_phase"])

    def test_a_capability_sized_exactly_to_the_mission_still_covers_it(self):
        part = _part(rated_total_dose_krad=51.75)
        result = supported_lifetime_months(part, PHASES)
        self.assertAlmostEqual(result["supported_months"], 60.0, places=9)
        self.assertIsNone(result["exhausted_in_phase"])

    def test_a_thin_capability_runs_out_inside_a_named_phase(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=30.0
        )
        result = supported_lifetime_months(part, PHASES)
        self.assertAlmostEqual(result["supported_months"], 41.0, places=9)
        self.assertEqual(result["exhausted_in_phase"], "operational-orbit")

    def test_the_binding_mechanism_is_named(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=30.0
        )
        result = supported_lifetime_months(part, PHASES)
        self.assertEqual(result["binding_mechanism"], MECHANISM_TOTAL_DOSE)

    def test_displacement_can_be_the_binding_mechanism(self):
        part = _part(rated_displacement_fluence=1.0e10)
        result = supported_lifetime_months(part, PHASES)
        self.assertEqual(result["binding_mechanism"], MECHANISM_DISPLACEMENT)
        self.assertLess(result["supported_months"], 60.0)

    def test_a_larger_margin_shortens_the_supported_lifetime(self):
        tight = supported_lifetime_months(
            _part(evidence_pedigree="manufacturer-datasheet-claim"), PHASES
        )
        loose = supported_lifetime_months(
            _part(evidence_pedigree=LOT_SPECIFIC_PEDIGREE), PHASES
        )
        self.assertLessEqual(tight["supported_months"], loose["supported_months"])

    def test_a_phase_with_no_dose_rate_costs_no_lifetime(self):
        phases = copy.deepcopy(PHASES)
        phases[0]["shielded_dose_rate_krad_per_month"] = 0.0
        phases[0]["shielded_fluence_rate_per_month"] = 0.0
        result = supported_lifetime_months(PART, phases)
        self.assertAlmostEqual(result["supported_months"], 60.0, places=9)

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            supported_lifetime_months("u-3001", PHASES)


class AssessmentTests(unittest.TestCase):
    def test_a_matched_part_is_accepted(self):
        result = assess_part(PART, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_ACCEPTED)
        self.assertTrue(result["acceptable"])

    def test_a_datasheet_pedigree_shortfall_buys_a_lot_test(self):
        part = _part(evidence_pedigree="manufacturer-datasheet-claim")
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_LOT_TEST)
        self.assertTrue(result["acceptable"])

    def test_a_small_shortfall_at_the_best_pedigree_buys_shielding(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=30.0
        )
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_SHIELDING)

    def test_a_large_shortfall_is_refused(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=10.0
        )
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_REFUSED)
        self.assertFalse(result["acceptable"])

    def test_a_destructive_mechanism_is_refused_whatever_the_dose_margin(self):
        part = _part(destructive_event_let_threshold=40.0)
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_REFUSED)

    def test_an_upset_rate_over_budget_asks_for_mitigation(self):
        part = _part(mitigated_upset_rate_per_day=5.0)
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_MITIGATION)

    def test_a_part_without_a_dose_capability_is_incomplete(self):
        part = _part()
        del part["rated_total_dose_krad"]
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_INCOMPLETE)
        self.assertFalse(result["acceptable"])

    def test_a_part_without_a_destructive_threshold_is_incomplete(self):
        part = _part()
        del part["destructive_event_let_threshold"]
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertEqual(result["verdict"], RAD_INCOMPLETE)

    def test_findings_name_the_phase_the_capability_runs_out_in(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=30.0
        )
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertTrue(
            any("operational-orbit" in finding for finding in result["findings"])
        )

    def test_the_lot_test_relief_is_reported_in_the_findings(self):
        part = _part(evidence_pedigree="manufacturer-datasheet-claim")
        result = assess_part(part, PHASES, ENVIRONMENT)
        self.assertTrue(any("lot" in finding for finding in result["findings"]))

    def test_the_accumulated_environment_is_returned_with_the_verdict(self):
        result = assess_part(PART, PHASES, ENVIRONMENT)
        self.assertAlmostEqual(
            result["environment"]["total_dose_krad"], 34.5, places=9
        )

    def test_a_part_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_part(_part(part_reference=""), PHASES, ENVIRONMENT)

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_part("u-3001", PHASES, ENVIRONMENT)

    def test_a_tighter_uplift_limit_turns_a_shielding_case_into_a_refusal(self):
        part = _part(
            evidence_pedigree=LOT_SPECIFIC_PEDIGREE, rated_total_dose_krad=30.0
        )
        result = assess_part(
            part, PHASES, ENVIRONMENT, {"shielding_uplift_limit": 1.05}
        )
        self.assertEqual(result["verdict"], RAD_REFUSED)


if __name__ == "__main__":
    unittest.main(verbosity=1)
