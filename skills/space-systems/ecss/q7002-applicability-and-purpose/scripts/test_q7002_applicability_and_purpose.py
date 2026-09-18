"""Contract tests for the outgassing-screening applicability and purpose logic."""

import unittest

from q7002_applicability_and_purpose_logic import (
    CVCM_LIMIT_PCT,
    DE_MINIMIS_EXPOSED_MASS_G,
    RML_LIMIT_PCT,
    TML_LIMIT_PCT,
    assess_material_screening,
    existing_data_is_reusable,
    recovered_mass_loss_pct,
    screening_required,
    screening_verdict,
)


def base_usage(**overrides):
    """A 12 g conformal coating on an externally vented box facing a radiator."""
    usage = {
        "material_designation": "coating type A",
        "processed_condition": "cured 24 h at 60 degC",
        "material_category": "conformal-coating",
        "environment": "vacuum",
        "exposed_mass_g": 12.0,
        "surfaces_in_view": ["thermal-control-radiator"],
    }
    usage.update(overrides)
    return usage


class RecoveredMassLossTests(unittest.TestCase):
    def test_water_vapour_is_removed_from_the_total(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(1.30, 0.45), 0.85, places=9)

    def test_zero_regain_leaves_the_total_unchanged(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(0.62, 0.0), 0.62, places=9)

    def test_regain_equal_to_the_total_gives_zero(self):
        self.assertAlmostEqual(recovered_mass_loss_pct(0.62, 0.62), 0.0, places=9)

    def test_regain_above_the_total_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct(0.62, 0.90)

    def test_negative_percent_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct(-0.1, 0.0)

    def test_percent_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct(140.0, 0.0)

    def test_non_numeric_percent_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_pct("1.30", 0.45)


class ApplicabilityTests(unittest.TestCase):
    def test_exposed_polymer_in_vacuum_owes_the_screening(self):
        usage = base_usage()
        del usage["surfaces_in_view"]
        self.assertTrue(screening_required(usage)["required"])

    def test_metal_is_exempt(self):
        result = screening_required(base_usage(material_category="metal-alloy"))
        self.assertFalse(result["required"])
        self.assertTrue(any("no organic volatile inventory" in r for r in result["reasons"]))

    def test_sealed_pressurised_volume_is_exempt(self):
        result = screening_required(base_usage(environment="sealed-pressurised-volume"))
        self.assertFalse(result["required"])
        self.assertTrue(any("cannot carry released volatiles" in r for r in result["reasons"]))

    def test_trace_mass_with_no_sensitive_surface_is_exempt(self):
        usage = base_usage(exposed_mass_g=0.2)
        del usage["surfaces_in_view"]
        result = screening_required(usage)
        self.assertFalse(result["required"])
        self.assertTrue(any("de-minimis" in r for r in result["reasons"]))

    def test_trace_mass_in_view_of_an_optic_still_owes_the_screening(self):
        usage = base_usage(exposed_mass_g=0.2, surfaces_in_view=["optical-element"])
        result = screening_required(usage)
        self.assertTrue(result["required"])
        self.assertTrue(any("optical-element" in r for r in result["reasons"]))

    def test_mass_exactly_at_the_de_minimis_owes_the_screening(self):
        usage = base_usage(exposed_mass_g=DE_MINIMIS_EXPOSED_MASS_G)
        del usage["surfaces_in_view"]
        self.assertTrue(screening_required(usage)["required"])

    def test_unlisted_category_is_treated_as_screened(self):
        usage = base_usage(material_category="bio-derived-binder")
        result = screening_required(usage)
        self.assertTrue(result["required"])
        self.assertTrue(any("not on the screened or the exempt list" in r for r in result["reasons"]))

    def test_vented_volume_carries_volatiles(self):
        self.assertTrue(screening_required(base_usage(environment="vented-volume"))["required"])

    def test_missing_required_key_rejected(self):
        usage = base_usage()
        del usage["environment"]
        with self.assertRaises(ValueError):
            screening_required(usage)

    def test_negative_exposed_mass_rejected(self):
        with self.assertRaises(ValueError):
            screening_required(base_usage(exposed_mass_g=-3.0))

    def test_non_mapping_usage_rejected(self):
        with self.assertRaises(ValueError):
            screening_required("coating type A")

    def test_surfaces_in_view_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            screening_required(base_usage(surfaces_in_view="optical-element"))


class ExistingDataTests(unittest.TestCase):
    def _data(self, **overrides):
        data = {
            "reference": "OGD-2211",
            "material_designation": "coating type A",
            "processed_condition": "cured 24 h at 60 degC",
        }
        data.update(overrides)
        return data

    def test_matching_designation_and_condition_is_reusable(self):
        self.assertTrue(existing_data_is_reusable(base_usage(), self._data()))

    def test_match_ignores_case(self):
        self.assertTrue(
            existing_data_is_reusable(base_usage(), self._data(material_designation="Coating Type A"))
        )

    def test_different_cure_state_is_not_reusable(self):
        self.assertFalse(
            existing_data_is_reusable(
                base_usage(), self._data(processed_condition="cured 2 h at 120 degC")
            )
        )

    def test_data_without_a_reference_is_not_reusable(self):
        self.assertFalse(existing_data_is_reusable(base_usage(), self._data(reference="")))

    def test_usage_without_a_processed_condition_is_not_reusable(self):
        usage = base_usage()
        del usage["processed_condition"]
        self.assertFalse(existing_data_is_reusable(usage, self._data()))

    def test_reusable_data_removes_the_screening_obligation(self):
        result = screening_required(base_usage(existing_data=self._data()))
        self.assertFalse(result["required"])
        self.assertEqual(result["reuse"], "OGD-2211")

    def test_non_matching_data_leaves_the_obligation(self):
        result = screening_required(
            base_usage(existing_data=self._data(material_designation="coating type B"))
        )
        self.assertTrue(result["required"])
        self.assertIsNone(result["reuse"])


class ScreeningVerdictTests(unittest.TestCase):
    def test_clean_result_passes(self):
        self.assertEqual(screening_verdict(0.42, 0.01)["verdict"], "pass")

    def test_result_exactly_on_both_limits_passes(self):
        result = screening_verdict(TML_LIMIT_PCT, CVCM_LIMIT_PCT)
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["tml_pct"], TML_LIMIT_PCT, places=9)
        self.assertAlmostEqual(result["cvcm_pct"], CVCM_LIMIT_PCT, places=9)

    def test_condensable_above_its_limit_fails_outright(self):
        result = screening_verdict(0.40, 0.25)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("condensable" in f for f in result["findings"]))

    def test_condensable_failure_is_not_rescued_by_water_regain(self):
        self.assertEqual(screening_verdict(1.40, 0.25, 0.60)["verdict"], "fail")

    def test_total_loss_above_its_limit_without_regain_data_fails(self):
        self.assertEqual(screening_verdict(1.40, 0.05)["verdict"], "fail")

    def test_water_regain_can_make_the_result_conditional(self):
        result = screening_verdict(1.40, 0.05, 0.60)
        self.assertEqual(result["verdict"], "conditional")
        self.assertAlmostEqual(result["rml_pct"], 0.80, places=9)

    def test_recovered_loss_still_over_the_limit_fails(self):
        result = screening_verdict(1.90, 0.05, 0.30)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("still above" in f for f in result["findings"]))

    def test_recovered_loss_exactly_on_its_limit_is_conditional(self):
        result = screening_verdict(1.50, 0.05, 0.50)
        self.assertAlmostEqual(result["rml_pct"], RML_LIMIT_PCT, places=9)
        self.assertEqual(result["verdict"], "conditional")

    def test_findings_are_empty_on_a_clean_pass(self):
        self.assertEqual(screening_verdict(0.30, 0.02)["findings"], [])

    def test_regain_without_a_total_loss_failure_stays_a_pass(self):
        self.assertEqual(screening_verdict(0.70, 0.03, 0.20)["verdict"], "pass")

    def test_non_numeric_result_rejected(self):
        with self.assertRaises(ValueError):
            screening_verdict("0.42", 0.01)


class CombinedAssessmentTests(unittest.TestCase):
    def test_owed_screening_with_no_results_reports_the_debt(self):
        self.assertEqual(assess_material_screening(base_usage())["status"], "screening-owed")

    def test_exempt_material_needs_no_results(self):
        result = assess_material_screening(base_usage(material_category="glass"))
        self.assertEqual(result["status"], "screening-not-required")
        self.assertIsNone(result["screening"])

    def test_clean_results_give_an_acceptable_status(self):
        result = assess_material_screening(
            base_usage(), {"tml_pct": 0.42, "cvcm_pct": 0.01}
        )
        self.assertEqual(result["status"], "screened-acceptable")

    def test_conditional_results_are_flagged_as_needing_justification(self):
        result = assess_material_screening(
            base_usage(),
            {"tml_pct": 1.40, "cvcm_pct": 0.05, "water_vapour_regained_pct": 0.60},
        )
        self.assertEqual(result["status"], "screened-acceptable-with-justification")

    def test_failing_results_are_rejected(self):
        result = assess_material_screening(base_usage(), {"tml_pct": 0.40, "cvcm_pct": 0.25})
        self.assertEqual(result["status"], "screened-rejected")

    def test_results_missing_a_required_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_screening(base_usage(), {"tml_pct": 0.40})

    def test_non_mapping_results_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_screening(base_usage(), [0.40, 0.01])

    def test_applicability_reasons_travel_with_the_assessment(self):
        result = assess_material_screening(base_usage())
        self.assertTrue(result["applicability"]["reasons"])


if __name__ == "__main__":
    unittest.main()
