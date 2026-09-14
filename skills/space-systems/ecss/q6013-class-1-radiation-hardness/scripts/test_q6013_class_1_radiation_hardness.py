#!/usr/bin/env python3
"""Contract test for the Class 1 radiation hardness decision (offline)."""

import copy
import unittest

from q6013_class_1_radiation_hardness_logic import (
    DEFAULT_RHA_POLICY,
    DESTRUCTIVE_IMMUNE,
    DESTRUCTIVE_SUSCEPTIBLE,
    EVIDENCE_BASES,
    MITIGATION_LEVELS,
    PART_NEEDS_LOT_TESTING,
    PART_NEEDS_MITIGATION,
    PART_NOT_SUITABLE,
    PART_SUITABLE,
    TID_CAPABLE,
    TID_SHORTFALL,
    UPSET_BUDGET_EXCEEDED,
    UPSET_BUDGET_MET,
    VERDICTS,
    assess_radiation_hardness,
    destructive_see_assessment,
    lot_radiation_test_required,
    mitigated_upset_rate_per_day,
    radiation_design_margin,
    required_part_tid_krad,
    tid_assessment,
    upset_assessment,
    validate_rha_policy,
)

GOOD_CASE = {
    "evidence_basis": "lot-radiation-test",
    "mission_tid_krad": 20.0,
    "part_tid_capability_krad": 60.0,
    "environment_let_max": 60.0,
    "part_destructive_let_threshold": 80.0,
    "raw_upset_rate_per_day": 5.0e-4,
    "mitigation_level": "none",
}

WEAK_CASE = {
    "evidence_basis": "similarity-argument",
    "mission_tid_krad": 20.0,
    "part_tid_capability_krad": 150.0,
    "environment_let_max": 60.0,
    "part_destructive_let_threshold": 80.0,
    "raw_upset_rate_per_day": 2.0e-4,
    "mitigation_level": "none",
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_rha_policy(DEFAULT_RHA_POLICY), DEFAULT_RHA_POLICY)

    def test_policy_covers_every_evidence_basis(self):
        for basis in EVIDENCE_BASES:
            self.assertIn(basis, DEFAULT_RHA_POLICY["design_margin_by_basis"])

    def test_policy_covers_every_mitigation_level(self):
        for level in MITIGATION_LEVELS:
            self.assertIn(level, DEFAULT_RHA_POLICY["mitigation_credit"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_rha_policy("default")

    def test_policy_missing_a_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_RHA_POLICY)
        del broken["design_margin_by_basis"]["heritage-data"]
        with self.assertRaises(ValueError):
            validate_rha_policy(broken)

    def test_policy_margin_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_RHA_POLICY)
        broken["design_margin_by_basis"]["lot-radiation-test"] = 0.5
        with self.assertRaises(ValueError):
            validate_rha_policy(broken)

    def test_policy_mitigation_credit_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_RHA_POLICY)
        broken["mitigation_credit"]["none"] = 2.0
        with self.assertRaises(ValueError):
            validate_rha_policy(broken)

    def test_policy_unknown_lot_test_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_RHA_POLICY)
        broken["bases_needing_lot_test"] = ("vendor-hunch",)
        with self.assertRaises(ValueError):
            validate_rha_policy(broken)


class DesignMarginTests(unittest.TestCase):
    def test_lot_tested_basis_earns_the_smallest_margin(self):
        values = [radiation_design_margin(b) for b in EVIDENCE_BASES]
        self.assertAlmostEqual(min(values), values[0], places=9)

    def test_margin_grows_as_the_basis_weakens(self):
        values = [radiation_design_margin(b) for b in EVIDENCE_BASES]
        for weaker, stronger in zip(values[1:], values):
            self.assertGreater(weaker - stronger, 1.0e-9)

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            radiation_design_margin("datasheet-hope")

    def test_required_dose_is_the_mission_dose_times_the_margin(self):
        self.assertAlmostEqual(
            required_part_tid_krad(20.0, "manufacturer-rha"), 40.0, places=9
        )

    def test_zero_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_part_tid_krad(0.0, "lot-radiation-test")

    def test_negative_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_part_tid_krad(-5.0, "lot-radiation-test")


class TidAssessmentTests(unittest.TestCase):
    def test_capable_part_reports_capable(self):
        result = tid_assessment(60.0, 20.0, "lot-radiation-test")
        self.assertEqual(result["verdict"], TID_CAPABLE)

    def test_short_part_reports_shortfall(self):
        result = tid_assessment(20.0, 20.0, "similarity-argument")
        self.assertEqual(result["verdict"], TID_SHORTFALL)

    def test_capability_exactly_on_the_requirement_is_capable(self):
        required = required_part_tid_krad(20.0, "manufacturer-rha")
        result = tid_assessment(required, 20.0, "manufacturer-rha")
        self.assertEqual(result["verdict"], TID_CAPABLE)
        self.assertAlmostEqual(result["margin_ratio"], 1.0, places=9)

    def test_representation_error_at_the_requirement_is_absorbed(self):
        required = required_part_tid_krad(20.0, "manufacturer-rha")
        drifted = required - required * 2.0e-16
        result = tid_assessment(drifted, 20.0, "manufacturer-rha")
        self.assertEqual(result["verdict"], TID_CAPABLE)

    def test_margin_ratio_matches_the_quotient(self):
        result = tid_assessment(120.0, 20.0, "manufacturer-rha")
        self.assertAlmostEqual(result["margin_ratio"], 3.0, places=9)

    def test_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            tid_assessment(0.0, 20.0, "lot-radiation-test")


class DestructiveSeeTests(unittest.TestCase):
    def test_threshold_above_the_environment_is_immune(self):
        result = destructive_see_assessment(80.0, 60.0)
        self.assertEqual(result["verdict"], DESTRUCTIVE_IMMUNE)

    def test_threshold_below_the_environment_is_susceptible(self):
        result = destructive_see_assessment(20.0, 60.0)
        self.assertEqual(result["verdict"], DESTRUCTIVE_SUSCEPTIBLE)

    def test_threshold_exactly_on_the_environment_is_immune(self):
        result = destructive_see_assessment(60.0, 60.0)
        self.assertTrue(result["immune"])

    def test_absent_threshold_is_treated_as_susceptible(self):
        result = destructive_see_assessment(None, 60.0)
        self.assertEqual(result["verdict"], DESTRUCTIVE_SUSCEPTIBLE)
        self.assertIn("no destructive single-event threshold", result["note"])

    def test_zero_environment_energy_rejected(self):
        with self.assertRaises(ValueError):
            destructive_see_assessment(80.0, 0.0)


class UpsetTests(unittest.TestCase):
    def test_no_mitigation_leaves_the_raw_rate(self):
        self.assertAlmostEqual(
            mitigated_upset_rate_per_day(1.0e-3, "none"), 1.0e-3, places=12
        )

    def test_scrubbing_takes_two_decades_of_credit(self):
        self.assertAlmostEqual(
            mitigated_upset_rate_per_day(1.0e-1, "correction-and-scrub"),
            1.0e-3,
            places=12,
        )

    def test_rate_exactly_on_the_budget_is_met(self):
        budget = DEFAULT_RHA_POLICY["upset_rate_budget_per_day"]
        result = upset_assessment(budget, "none")
        self.assertEqual(result["verdict"], UPSET_BUDGET_MET)

    def test_rate_above_the_budget_is_exceeded(self):
        result = upset_assessment(1.0, "none")
        self.assertEqual(result["verdict"], UPSET_BUDGET_EXCEEDED)

    def test_unknown_mitigation_level_rejected(self):
        with self.assertRaises(ValueError):
            upset_assessment(1.0e-4, "hope")

    def test_negative_raw_rate_rejected(self):
        with self.assertRaises(ValueError):
            upset_assessment(-1.0e-4, "none")


class LotTestTests(unittest.TestCase):
    def test_lot_tested_basis_needs_no_further_lot_test(self):
        self.assertFalse(lot_radiation_test_required("lot-radiation-test", 1.0))

    def test_similarity_basis_always_needs_a_lot_test(self):
        self.assertTrue(lot_radiation_test_required("similarity-argument", 50.0))

    def test_heritage_basis_always_needs_a_lot_test(self):
        self.assertTrue(lot_radiation_test_required("heritage-data", 50.0))

    def test_maker_declaration_with_thin_margin_needs_a_lot_test(self):
        self.assertTrue(lot_radiation_test_required("manufacturer-rha", 1.2))

    def test_maker_declaration_with_fat_margin_needs_no_lot_test(self):
        self.assertFalse(lot_radiation_test_required("manufacturer-rha", 4.0))

    def test_margin_exactly_on_the_lot_test_trigger_needs_no_lot_test(self):
        trigger = DEFAULT_RHA_POLICY["lot_test_required_below_margin"]
        self.assertFalse(lot_radiation_test_required("manufacturer-rha", trigger))


class AssessRadiationHardnessTests(unittest.TestCase):
    def test_lot_tested_capable_part_is_suitable(self):
        result = assess_radiation_hardness(GOOD_CASE)
        self.assertEqual(result["verdict"], PART_SUITABLE)
        self.assertEqual(result["findings"], [])

    def test_susceptible_part_is_not_suitable(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, part_destructive_let_threshold=15.0)
        )
        self.assertEqual(result["verdict"], PART_NOT_SUITABLE)

    def test_dose_shortfall_is_not_suitable(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, part_tid_capability_krad=10.0)
        )
        self.assertEqual(result["verdict"], PART_NOT_SUITABLE)

    def test_similarity_basis_drives_lot_testing(self):
        result = assess_radiation_hardness(WEAK_CASE)
        self.assertEqual(result["verdict"], PART_NEEDS_LOT_TESTING)
        self.assertTrue(result["lot_radiation_test_required"])

    def test_upset_budget_breach_drives_mitigation(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, raw_upset_rate_per_day=5.0e-2)
        )
        self.assertEqual(result["verdict"], PART_NEEDS_MITIGATION)

    def test_mitigation_can_recover_the_upset_budget(self):
        result = assess_radiation_hardness(
            _case(
                GOOD_CASE,
                raw_upset_rate_per_day=5.0e-2,
                mitigation_level="correction-and-scrub",
            )
        )
        self.assertEqual(result["verdict"], PART_SUITABLE)

    def test_requirement_relief_is_zero_on_a_lot_tested_basis(self):
        result = assess_radiation_hardness(GOOD_CASE)
        self.assertAlmostEqual(result["tid_requirement_relief_krad"], 0.0, places=9)

    def test_requirement_relief_is_positive_on_a_weak_basis(self):
        result = assess_radiation_hardness(WEAK_CASE)
        self.assertGreater(result["tid_requirement_relief_krad"], 1.0e-6)

    def test_every_verdict_is_a_known_token(self):
        for basis in EVIDENCE_BASES:
            result = assess_radiation_hardness(_case(WEAK_CASE, evidence_basis=basis))
            self.assertIn(result["verdict"], VERDICTS)

    def test_unknown_basis_in_a_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness(_case(GOOD_CASE, evidence_basis="vendor-word"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness(["lot-radiation-test"])

    def test_missing_destructive_threshold_is_reported(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, part_destructive_let_threshold=None)
        )
        self.assertEqual(result["verdict"], PART_NOT_SUITABLE)
        self.assertTrue(any("destructive single-event" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
