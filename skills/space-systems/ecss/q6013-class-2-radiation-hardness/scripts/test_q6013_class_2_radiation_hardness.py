#!/usr/bin/env python3
"""Contract test for the Class 2 radiation hardness criteria (offline)."""

import copy
import unittest

from q6013_class_2_radiation_hardness_logic import (
    DESIGN_MARGIN,
    DESTRUCTIVE_PROTECTIONS,
    EVIDENCE_BASES,
    NEEDS_LOT_RADIATION_TESTING,
    NEEDS_UPSET_MITIGATION,
    NOT_SUITABLE,
    SUITABLE,
    THIN_MARGIN_RATIO,
    UPSET_MITIGATIONS,
    assess_destructive_events,
    assess_radiation_hardness,
    assess_total_dose,
    assess_upset_rate,
    dose_relief_krad,
    lot_test_required,
    radiation_design_margin,
    required_dose_krad,
)

GOOD_CASE = {
    "evidence_basis": "lot-radiation-test",
    "mission_dose_krad": 20.0,
    "capability_krad": 100.0,
    "environment_let": 60.0,
    "destructive_threshold_let": 75.0,
    "predicted_destructive_rate_per_day": None,
    "destructive_protection": "none",
    "destructive_allowance_per_day": 0.0,
    "raw_upset_rate_per_day": 1.0e-4,
    "upset_mitigation": "scrubbing",
    "upset_budget_per_day": 1.0e-3,
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class DesignMarginTests(unittest.TestCase):
    def test_every_basis_carries_a_margin(self):
        for basis in EVIDENCE_BASES:
            self.assertIn(basis, DESIGN_MARGIN)

    def test_margin_widens_as_the_evidence_weakens(self):
        margins = [radiation_design_margin(basis) for basis in EVIDENCE_BASES]
        for stronger, weaker in zip(margins, margins[1:]):
            self.assertGreater(weaker - stronger, 1.0e-6)

    def test_lot_tested_basis_carries_the_narrowest_margin(self):
        self.assertAlmostEqual(
            radiation_design_margin("lot-radiation-test"), 1.2, places=9
        )

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            radiation_design_margin("word-of-mouth")

    def test_required_dose_is_the_margined_mission_dose(self):
        self.assertAlmostEqual(
            required_dose_krad(20.0, "heritage-data"), 40.0, places=9
        )

    def test_zero_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_dose_krad(0.0, "heritage-data")


class TotalDoseTests(unittest.TestCase):
    def test_ample_capability_is_covered(self):
        dose = assess_total_dose(100.0, 20.0, "lot-radiation-test")
        self.assertTrue(dose["covered"])
        self.assertGreater(dose["margin_ratio"], 1.0)

    def test_capability_exactly_on_the_requirement_is_covered(self):
        required = required_dose_krad(20.0, "manufacturer-rha")
        dose = assess_total_dose(required, 20.0, "manufacturer-rha")
        self.assertTrue(dose["covered"])
        self.assertAlmostEqual(dose["margin_ratio"], 1.0, places=9)

    def test_representation_error_at_the_requirement_is_absorbed(self):
        required = required_dose_krad(20.0, "manufacturer-rha")
        drifted = required - required * 2.0e-16
        self.assertTrue(assess_total_dose(drifted, 20.0, "manufacturer-rha")["covered"])

    def test_capability_short_of_the_requirement_is_not_covered(self):
        dose = assess_total_dose(25.0, 20.0, "similarity-argument")
        self.assertFalse(dose["covered"])

    def test_bare_mission_dose_is_not_the_requirement(self):
        dose = assess_total_dose(25.0, 20.0, "heritage-data")
        self.assertGreater(dose["required_dose_krad"], dose["mission_dose_krad"])

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            assess_total_dose(-5.0, 20.0, "heritage-data")


class DestructiveEventTests(unittest.TestCase):
    def test_threshold_above_the_environment_is_immune(self):
        result = assess_destructive_events(80.0, 60.0)
        self.assertTrue(result["immune"])
        self.assertTrue(result["acceptable"])

    def test_threshold_exactly_on_the_environment_is_immune(self):
        result = assess_destructive_events(60.0, 60.0)
        self.assertTrue(result["immune"])

    def test_susceptible_part_without_protection_is_not_acceptable(self):
        result = assess_destructive_events(20.0, 60.0, 1.0e-6, "none", 1.0e-3)
        self.assertFalse(result["acceptable"])
        self.assertIn("no rate credit", result["reason"])

    def test_susceptible_part_behind_protection_inside_the_allowance(self):
        result = assess_destructive_events(
            20.0, 60.0, 1.0e-4, "current-limiting", 1.0e-4
        )
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(
            result["protected_rate_per_day"], 1.0e-5, places=12
        )

    def test_protected_rate_exactly_on_the_allowance_is_acceptable(self):
        credit = DESTRUCTIVE_PROTECTIONS["current-limiting-with-power-cycling"]
        allowance = 1.0 * (1.0 - credit)
        result = assess_destructive_events(
            20.0, 60.0, 1.0, "current-limiting-with-power-cycling", allowance
        )
        self.assertTrue(result["acceptable"])

    def test_protected_rate_above_the_allowance_is_not_acceptable(self):
        result = assess_destructive_events(
            20.0, 60.0, 1.0, "current-limiting", 1.0e-6
        )
        self.assertFalse(result["acceptable"])

    def test_undeclared_threshold_is_carried_as_susceptible(self):
        result = assess_destructive_events(None, 60.0)
        self.assertFalse(result["immune"])
        self.assertFalse(result["acceptable"])
        self.assertIn("susceptible", result["reason"])

    def test_undeclared_threshold_may_still_be_carried_behind_protection(self):
        result = assess_destructive_events(
            None, 60.0, 1.0e-4, "current-limiting", 1.0e-4
        )
        self.assertTrue(result["acceptable"])

    def test_susceptible_part_with_no_rate_has_nothing_to_argue_with(self):
        result = assess_destructive_events(20.0, 60.0, None, "current-limiting", 1.0)
        self.assertFalse(result["acceptable"])
        self.assertIn("no predicted destructive rate", result["reason"])

    def test_unknown_protection_rejected(self):
        with self.assertRaises(ValueError):
            assess_destructive_events(20.0, 60.0, 1.0e-4, "crossed-fingers", 1.0)

    def test_zero_environment_energy_rejected(self):
        with self.assertRaises(ValueError):
            assess_destructive_events(20.0, 0.0)


class UpsetRateTests(unittest.TestCase):
    def test_every_mitigation_level_carries_a_credit(self):
        for level, credit in UPSET_MITIGATIONS.items():
            self.assertGreaterEqual(credit, 0.0)
            self.assertLessEqual(credit, 1.0)
            self.assertIsInstance(level, str)

    def test_mitigation_reduces_the_residual_rate(self):
        bare = assess_upset_rate(1.0e-3, "none", 1.0e-3)
        scrubbed = assess_upset_rate(1.0e-3, "scrubbing", 1.0e-3)
        self.assertGreater(
            bare["residual_rate_per_day"] - scrubbed["residual_rate_per_day"],
            1.0e-9,
        )

    def test_residual_inside_the_budget_passes(self):
        self.assertTrue(
            assess_upset_rate(1.0e-3, "scrubbing", 1.0e-3)["within_budget"]
        )

    def test_residual_exactly_on_the_budget_passes(self):
        raw = 1.0e-3
        budget = raw * (1.0 - UPSET_MITIGATIONS["redundancy-with-scrubbing"])
        self.assertTrue(
            assess_upset_rate(raw, "redundancy-with-scrubbing", budget)[
                "within_budget"
            ]
        )

    def test_residual_above_the_budget_fails(self):
        self.assertFalse(
            assess_upset_rate(1.0, "detection-only", 1.0e-6)["within_budget"]
        )

    def test_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            assess_upset_rate(1.0e-3, "hope", 1.0e-3)

    def test_negative_raw_rate_rejected(self):
        with self.assertRaises(ValueError):
            assess_upset_rate(-1.0, "none", 1.0)


class LotTestTriggerTests(unittest.TestCase):
    def test_lot_tested_basis_needs_no_further_lot_test(self):
        self.assertFalse(lot_test_required("lot-radiation-test", 1.0))

    def test_heritage_always_compels_a_lot_test(self):
        self.assertTrue(lot_test_required("heritage-data", 10.0))

    def test_similarity_always_compels_a_lot_test(self):
        self.assertTrue(lot_test_required("similarity-argument", 10.0))

    def test_thin_maker_declaration_compels_a_lot_test(self):
        self.assertTrue(lot_test_required("manufacturer-rha", 1.05))

    def test_maker_declaration_exactly_on_the_thin_ratio_does_not(self):
        self.assertFalse(lot_test_required("manufacturer-rha", THIN_MARGIN_RATIO))

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            lot_test_required("a-good-feeling", 2.0)


class DoseReliefTests(unittest.TestCase):
    def test_relief_is_the_gap_to_a_lot_tested_basis(self):
        self.assertAlmostEqual(
            dose_relief_krad(20.0, "similarity-argument"), 36.0, places=9
        )

    def test_lot_tested_basis_has_nothing_to_buy_back(self):
        self.assertAlmostEqual(
            dose_relief_krad(20.0, "lot-radiation-test"), 0.0, places=9
        )


class AssessRadiationHardnessTests(unittest.TestCase):
    def test_well_evidenced_part_is_suitable(self):
        result = assess_radiation_hardness(GOOD_CASE)
        self.assertEqual(result["verdict"], SUITABLE)
        self.assertTrue(result["suitable"])
        self.assertEqual(result["findings"], [])

    def test_dose_shortfall_makes_the_part_unsuitable(self):
        result = assess_radiation_hardness(_case(GOOD_CASE, capability_krad=5.0))
        self.assertEqual(result["verdict"], NOT_SUITABLE)
        self.assertTrue(any("dose capability" in f for f in result["findings"]))

    def test_unprotected_susceptible_part_is_unsuitable(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, destructive_threshold_let=10.0)
        )
        self.assertEqual(result["verdict"], NOT_SUITABLE)
        self.assertTrue(
            any("destructive single events" in f for f in result["findings"])
        )

    def test_protected_susceptible_part_may_still_be_carried(self):
        result = assess_radiation_hardness(
            _case(
                GOOD_CASE,
                destructive_threshold_let=10.0,
                predicted_destructive_rate_per_day=1.0e-4,
                destructive_protection="current-limiting",
                destructive_allowance_per_day=1.0e-4,
            )
        )
        self.assertEqual(result["verdict"], SUITABLE)

    def test_heritage_basis_asks_for_a_lot_radiation_test(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, evidence_basis="heritage-data")
        )
        self.assertEqual(result["verdict"], NEEDS_LOT_RADIATION_TESTING)
        self.assertTrue(result["lot_test_required"])

    def test_upset_budget_breach_asks_for_mitigation(self):
        result = assess_radiation_hardness(
            _case(
                GOOD_CASE,
                raw_upset_rate_per_day=1.0,
                upset_mitigation="none",
                upset_budget_per_day=1.0e-6,
            )
        )
        self.assertEqual(result["verdict"], NEEDS_UPSET_MITIGATION)

    def test_weak_basis_reports_the_relief_a_lot_test_would_buy(self):
        result = assess_radiation_hardness(
            _case(GOOD_CASE, evidence_basis="similarity-argument")
        )
        self.assertGreater(result["dose_relief_krad"], 1.0e-6)

    def test_uncategorized_basis_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness(_case(GOOD_CASE, evidence_basis=None))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness(["lot-radiation-test"])

    def test_every_basis_produces_a_graded_verdict(self):
        for basis in EVIDENCE_BASES:
            result = assess_radiation_hardness(
                _case(GOOD_CASE, evidence_basis=basis, capability_krad=500.0)
            )
            self.assertIn(
                result["verdict"], (SUITABLE, NEEDS_LOT_RADIATION_TESTING)
            )


if __name__ == "__main__":
    unittest.main(verbosity=1)
