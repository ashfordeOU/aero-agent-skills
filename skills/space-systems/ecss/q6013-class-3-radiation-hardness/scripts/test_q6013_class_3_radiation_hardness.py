"""Contract tests for the clause 6.2.2.4 Class 3 radiation-hardness logic."""

import unittest

from q6013_class_3_radiation_hardness_logic import (
    CLASS_3_DESIGN_MARGINS,
    THIN_DOSE_RATIO,
    assess_radiation_hardness,
    design_margin,
    destructive_disposition,
    dose_disposition,
    dose_relief_krad,
    lot_screening_required,
    mitigated_upset_rate,
    protected_destructive_rate,
    required_dose_krad,
    upset_disposition,
)


def clean_declaration(**overrides):
    """A part whose evidence closes every effect at the lowest assurance class."""
    declaration = {
        "evidence_basis": "lot-radiation-test",
        "function_criticality": "mission-critical",
        "mission_dose_krad": 10.0,
        "dose_capability_krad": 20.0,
        "environment_ion_energy_mev_cm2_mg": 60.0,
        "destructive_threshold_mev_cm2_mg": 75.0,
        "raw_upset_rate_per_day": 1.0e-4,
        "upset_mitigation_factor": 0.1,
        "upset_budget_per_day": 1.0e-4,
    }
    declaration.update(overrides)
    return declaration


class DesignMarginTests(unittest.TestCase):
    def test_lot_screened_basis_carries_the_thinnest_margin(self):
        self.assertAlmostEqual(design_margin("lot-radiation-test"), 1.2, places=9)

    def test_margin_widens_as_evidence_leaves_the_delivered_lot(self):
        self.assertGreater(
            design_margin("similarity-argument"), design_margin("heritage-flight-data")
        )

    def test_every_tabulated_basis_carries_a_margin_above_unity(self):
        for basis, margin in CLASS_3_DESIGN_MARGINS.items():
            self.assertGreater(margin, 1.0, basis)

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            design_margin("vendor-said-it-is-fine")

    def test_absent_evidence_cannot_size_a_requirement(self):
        with self.assertRaises(ValueError):
            design_margin("no-radiation-data")


class RequiredDoseTests(unittest.TestCase):
    def test_requirement_is_the_margined_mission_dose(self):
        self.assertAlmostEqual(
            required_dose_krad(10.0, "manufacturer-rha-declaration"), 15.0, places=9
        )

    def test_generic_family_data_costs_the_most_dose(self):
        self.assertAlmostEqual(
            required_dose_krad(10.0, "generic-family-data"), 50.0, places=9
        )

    def test_negative_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_dose_krad(-1.0, "lot-radiation-test")

    def test_non_numeric_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_dose_krad("10", "lot-radiation-test")

    def test_boolean_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            required_dose_krad(True, "lot-radiation-test")


class DoseDispositionTests(unittest.TestCase):
    def test_capability_above_requirement_is_covered(self):
        self.assertEqual(dose_disposition(30.0, 15.0), "dose-covered")

    def test_capability_exactly_on_the_requirement_is_covered(self):
        self.assertEqual(dose_disposition(15.0, 15.0), "dose-covered")

    def test_capability_below_requirement_is_short(self):
        self.assertEqual(dose_disposition(12.0, 15.0), "dose-short")

    def test_undeclared_capability_is_its_own_disposition(self):
        self.assertEqual(dose_disposition(None, 15.0), "dose-capability-undeclared")

    def test_relief_is_the_gap_back_to_a_lot_screened_basis(self):
        self.assertAlmostEqual(dose_relief_krad(10.0, "similarity-argument"), 18.0, places=9)

    def test_relief_on_a_lot_screened_basis_is_zero(self):
        self.assertAlmostEqual(dose_relief_krad(10.0, "lot-radiation-test"), 0.0, places=9)


class DestructiveEventTests(unittest.TestCase):
    def test_threshold_above_the_environment_is_immune(self):
        self.assertEqual(
            destructive_disposition(75.0, 60.0, "mission-critical"), "destructive-immune"
        )

    def test_threshold_exactly_on_the_environment_is_immune(self):
        self.assertEqual(
            destructive_disposition(60.0, 60.0, "mission-critical"), "destructive-immune"
        )

    def test_undeclared_threshold_is_carried_as_susceptible(self):
        self.assertEqual(
            destructive_disposition(None, 60.0, "mission-critical"), "destructive-susceptible"
        )

    def test_protected_rate_inside_the_allowance_is_accepted(self):
        self.assertEqual(
            destructive_disposition(
                20.0, 60.0, "mission-critical", 1.0e-3, 1.0e-4, 0.05
            ),
            "destructive-protected-rate-accepted",
        )

    def test_protected_rate_outside_the_allowance_stays_susceptible(self):
        self.assertEqual(
            destructive_disposition(20.0, 60.0, "mission-critical", 1.0e-2, 1.0e-6, 0.5),
            "destructive-susceptible",
        )

    def test_bare_rate_credit_opens_only_on_a_non_critical_function(self):
        self.assertEqual(
            destructive_disposition(20.0, 60.0, "non-critical", 1.0e-5, 1.0e-4),
            "destructive-bare-rate-accepted",
        )

    def test_bare_rate_credit_refused_on_a_critical_function(self):
        self.assertEqual(
            destructive_disposition(20.0, 60.0, "mission-critical", 1.0e-5, 1.0e-4),
            "destructive-susceptible",
        )

    def test_bare_rate_over_the_allowance_stays_susceptible(self):
        self.assertEqual(
            destructive_disposition(20.0, 60.0, "non-critical", 1.0e-2, 1.0e-4),
            "destructive-susceptible",
        )

    def test_protection_factor_scales_the_predicted_rate(self):
        self.assertAlmostEqual(protected_destructive_rate(2.0e-3, 0.05), 1.0e-4, places=12)

    def test_protection_factor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            protected_destructive_rate(1.0e-3, 1.5)

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            destructive_disposition(20.0, 60.0, "somewhat-important")


class UpsetBudgetTests(unittest.TestCase):
    def test_mitigation_scales_the_raw_rate(self):
        self.assertAlmostEqual(mitigated_upset_rate(1.0e-3, 0.1), 1.0e-4, places=12)

    def test_unmitigated_rate_passes_through(self):
        self.assertAlmostEqual(mitigated_upset_rate(1.0e-3, 1.0), 1.0e-3, places=12)

    def test_residual_inside_the_budget_passes(self):
        self.assertEqual(upset_disposition(1.0e-5, 1.0e-4), "upset-rate-within-budget")

    def test_residual_exactly_on_the_budget_passes(self):
        self.assertEqual(upset_disposition(1.0e-4, 1.0e-4), "upset-rate-within-budget")

    def test_residual_over_the_budget_fails(self):
        self.assertEqual(upset_disposition(1.0e-3, 1.0e-4), "upset-rate-over-budget")

    def test_zero_mitigation_factor_rejected(self):
        with self.assertRaises(ValueError):
            mitigated_upset_rate(1.0e-3, 0.0)


class LotScreeningTests(unittest.TestCase):
    def test_heritage_basis_always_compels_screening(self):
        self.assertTrue(lot_screening_required("heritage-flight-data", 10.0))

    def test_lot_screened_basis_never_compels_screening(self):
        self.assertFalse(lot_screening_required("lot-radiation-test", 1.0))

    def test_thin_dose_headroom_compels_screening_on_a_maker_declaration(self):
        self.assertTrue(
            lot_screening_required("manufacturer-rha-declaration", THIN_DOSE_RATIO / 2.0)
        )

    def test_ample_dose_headroom_leaves_a_maker_declaration_alone(self):
        self.assertFalse(
            lot_screening_required("manufacturer-rha-declaration", THIN_DOSE_RATIO * 2.0)
        )

    def test_missing_ratio_compels_screening(self):
        self.assertTrue(lot_screening_required("manufacturer-rha-declaration", None))

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            lot_screening_required("gut-feel", 3.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_part_is_suitable_with_no_findings(self):
        result = assess_radiation_hardness("U1", clean_declaration())
        self.assertEqual(result["verdict"], "suitable-at-class-3")
        self.assertEqual(result["findings"], [])

    def test_short_dose_is_not_suitable(self):
        result = assess_radiation_hardness(
            "U2", clean_declaration(dose_capability_krad=5.0)
        )
        self.assertEqual(result["dose_disposition"], "dose-short")
        self.assertEqual(result["verdict"], "not-suitable-at-class-3")

    def test_heritage_basis_drives_screening_and_reports_the_relief(self):
        result = assess_radiation_hardness(
            "U3",
            clean_declaration(
                evidence_basis="heritage-flight-data", dose_capability_krad=40.0
            ),
        )
        self.assertTrue(result["lot_screening_required"])
        self.assertEqual(result["verdict"], "needs-lot-radiation-screening")
        self.assertAlmostEqual(result["dose_relief_krad"], 8.0, places=9)

    def test_over_budget_upset_rate_asks_for_mitigation(self):
        result = assess_radiation_hardness(
            "U4", clean_declaration(upset_mitigation_factor=1.0, upset_budget_per_day=1.0e-6)
        )
        self.assertEqual(result["verdict"], "needs-upset-mitigation")

    def test_bare_rate_credit_restricts_a_critical_function(self):
        result = assess_radiation_hardness(
            "U5",
            clean_declaration(
                function_criticality="non-critical",
                destructive_threshold_mev_cm2_mg=20.0,
                predicted_destructive_rate_per_day=1.0e-5,
                destructive_allowance_per_day=1.0e-4,
            ),
        )
        self.assertEqual(result["destructive_disposition"], "destructive-bare-rate-accepted")
        self.assertIn(
            "bare-destructive-rate-credit-restricts-part-to-non-critical-use",
            result["findings"],
        )

    def test_susceptible_critical_part_is_not_suitable(self):
        result = assess_radiation_hardness(
            "U6", clean_declaration(destructive_threshold_mev_cm2_mg=20.0)
        )
        self.assertEqual(result["verdict"], "not-suitable-at-class-3")

    def test_absent_evidence_basis_is_reported_and_screened(self):
        result = assess_radiation_hardness(
            "U7", clean_declaration(evidence_basis="no-radiation-data")
        )
        self.assertIsNone(result["required_dose_krad"])
        self.assertTrue(result["lot_screening_required"])
        self.assertIn("no-radiation-evidence-basis-declared", result["findings"])

    def test_dose_ratio_is_capability_over_requirement(self):
        result = assess_radiation_hardness("U8", clean_declaration())
        self.assertAlmostEqual(result["dose_ratio"], 20.0 / 12.0, places=9)

    def test_missing_required_key_rejected(self):
        declaration = clean_declaration()
        del declaration["mission_dose_krad"]
        with self.assertRaises(ValueError):
            assess_radiation_hardness("U9", declaration)

    def test_empty_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness("   ", clean_declaration())

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness("U10", ["evidence_basis"])

    def test_unknown_criticality_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_radiation_hardness(
                "U11", clean_declaration(function_criticality="fairly-critical")
            )


if __name__ == "__main__":
    unittest.main()
