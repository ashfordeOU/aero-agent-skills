"""Contract tests for crew-compartment material control from offgassing results."""

import math
import unittest

from q7029_crewed_material_control_logic import (
    BOUND_TOLERANCE,
    DEFAULT_REVALIDATION_DAYS,
    MAX_TOXICITY_INDEX,
    REQUIRED_EVIDENCE,
    UG_PER_MG,
    assess_crewed_material_control,
    cabin_concentration_mg_m3,
    binding_compound,
    combined_mass_limit_g,
    compound_contributions,
    missing_evidence,
    report_currency_findings,
    selection_disposition,
    single_compound_mass_limit_g,
    smac_ratio,
    toxicity_index,
)


def _compounds(**over):
    base = [
        {"name": "alcohol-a", "yield_ug_per_g": 40.0, "smac_mg_m3": 40.0},
        {"name": "aldehyde-b", "yield_ug_per_g": 5.0, "smac_mg_m3": 0.05},
    ]
    if "compounds" in over:
        return over["compounds"]
    return base


def _spec(**over):
    base = {
        "compounds": _compounds(),
        "installed_mass_g": 500.0,
        "free_volume_m3": 100.0,
        "evidence_held": list(REQUIRED_EVIDENCE),
        "days_since_test": 200.0,
        "formulation_changed": False,
    }
    base.update(over)
    return base


class ConcentrationTests(unittest.TestCase):
    def test_concentration_scales_with_installed_mass(self):
        one = cabin_concentration_mg_m3(100.0, 5.0, 50.0)
        two = cabin_concentration_mg_m3(200.0, 5.0, 50.0)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_concentration_falls_with_free_volume(self):
        small = cabin_concentration_mg_m3(100.0, 5.0, 10.0)
        large = cabin_concentration_mg_m3(100.0, 5.0, 100.0)
        self.assertAlmostEqual(small, 10.0 * large, places=9)

    def test_concentration_is_micrograms_converted_to_milligrams(self):
        value = cabin_concentration_mg_m3(1000.0, 1.0, 1.0)
        self.assertAlmostEqual(value, 1000.0 / UG_PER_MG, places=9)

    def test_zero_installed_mass_contributes_nothing(self):
        self.assertAlmostEqual(cabin_concentration_mg_m3(0.0, 9.0, 20.0), 0.0, places=9)

    def test_zero_free_volume_rejected(self):
        with self.assertRaises(ValueError):
            cabin_concentration_mg_m3(10.0, 1.0, 0.0)

    def test_negative_yield_rejected(self):
        with self.assertRaises(ValueError):
            cabin_concentration_mg_m3(10.0, -1.0, 5.0)

    def test_boolean_mass_rejected(self):
        with self.assertRaises(ValueError):
            cabin_concentration_mg_m3(True, 1.0, 5.0)

    def test_smac_ratio_is_contribution_over_allowable(self):
        self.assertAlmostEqual(smac_ratio(5.0, 20.0), 0.25, places=9)

    def test_zero_allowable_rejected(self):
        with self.assertRaises(ValueError):
            smac_ratio(1.0, 0.0)


class MixtureTests(unittest.TestCase):
    def test_contributions_carry_one_record_per_compound(self):
        records = compound_contributions(_compounds(), 500.0, 100.0)
        self.assertEqual([r["name"] for r in records], ["alcohol-a", "aldehyde-b"])

    def test_compound_names_are_normalised(self):
        records = compound_contributions(
            [{"name": "  Alcohol-A ", "yield_ug_per_g": 1.0, "smac_mg_m3": 10.0}],
            100.0, 10.0,
        )
        self.assertEqual(records[0]["name"], "alcohol-a")

    def test_a_compound_reported_twice_is_rejected(self):
        duplicated = [
            {"name": "alcohol-a", "yield_ug_per_g": 1.0, "smac_mg_m3": 10.0},
            {"name": "ALCOHOL-A", "yield_ug_per_g": 2.0, "smac_mg_m3": 10.0},
        ]
        with self.assertRaises(ValueError):
            compound_contributions(duplicated, 100.0, 10.0)

    def test_the_index_is_the_sum_of_the_ratios(self):
        records = compound_contributions(_compounds(), 500.0, 100.0)
        self.assertAlmostEqual(
            toxicity_index(records),
            sum(r["smac_ratio"] for r in records),
            places=9,
        )

    def test_the_index_is_not_the_worst_single_ratio(self):
        records = compound_contributions(_compounds(), 500.0, 100.0)
        worst = max(r["smac_ratio"] for r in records)
        self.assertGreater(toxicity_index(records), worst)

    def test_an_empty_compound_list_is_rejected(self):
        with self.assertRaises(ValueError):
            compound_contributions([], 100.0, 10.0)

    def test_a_compound_missing_its_allowable_is_rejected(self):
        with self.assertRaises(ValueError):
            compound_contributions([{"name": "x", "yield_ug_per_g": 1.0}], 100.0, 10.0)

    def test_index_rejects_a_record_without_a_ratio(self):
        with self.assertRaises(ValueError):
            toxicity_index([{"name": "x"}])


class MassLimitTests(unittest.TestCase):
    def test_a_single_compound_limit_puts_it_exactly_on_its_allowable(self):
        limit = single_compound_mass_limit_g(5.0, 0.05, 100.0)
        reached = cabin_concentration_mg_m3(limit, 5.0, 100.0)
        self.assertAlmostEqual(reached, 0.05, places=9)

    def test_the_combined_limit_puts_the_mixture_exactly_on_unity(self):
        limit = combined_mass_limit_g(_compounds(), 100.0)
        records = compound_contributions(_compounds(), limit, 100.0)
        self.assertAlmostEqual(toxicity_index(records), MAX_TOXICITY_INDEX, places=9)

    def test_the_combined_limit_is_tighter_than_any_single_compound_limit(self):
        combined = combined_mass_limit_g(_compounds(), 100.0)
        singles = [
            single_compound_mass_limit_g(c["yield_ug_per_g"], c["smac_mg_m3"], 100.0)
            for c in _compounds()
        ]
        self.assertLess(combined, min(singles))

    def test_a_material_that_releases_nothing_has_no_mass_limit(self):
        inert = [{"name": "inert-a", "yield_ug_per_g": 0.0, "smac_mg_m3": 10.0}]
        self.assertTrue(math.isinf(combined_mass_limit_g(inert, 50.0)))

    def test_a_zero_yield_has_no_single_compound_limit_to_compute(self):
        with self.assertRaises(ValueError):
            single_compound_mass_limit_g(0.0, 10.0, 50.0)

    def test_combined_limit_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            combined_mass_limit_g([], 50.0)


class EvidenceTests(unittest.TestCase):
    def test_a_complete_record_is_missing_nothing(self):
        self.assertEqual(missing_evidence(list(REQUIRED_EVIDENCE)), [])

    def test_evidence_names_compare_without_case(self):
        upper = [name.upper() for name in REQUIRED_EVIDENCE]
        self.assertEqual(missing_evidence(upper), [])

    def test_a_missing_selection_approval_is_named(self):
        held = [n for n in REQUIRED_EVIDENCE if n != "material-selection-approval-70c"]
        self.assertEqual(missing_evidence(held), ["material-selection-approval-70c"])

    def test_an_empty_record_names_every_required_item(self):
        self.assertEqual(missing_evidence([]), list(REQUIRED_EVIDENCE))

    def test_a_blank_evidence_token_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence(["  "])

    def test_a_report_inside_its_interval_raises_nothing(self):
        self.assertEqual(
            report_currency_findings(100.0, DEFAULT_REVALIDATION_DAYS, False), []
        )

    def test_a_report_exactly_on_its_interval_is_still_current(self):
        self.assertEqual(
            report_currency_findings(
                DEFAULT_REVALIDATION_DAYS, DEFAULT_REVALIDATION_DAYS, False
            ),
            [],
        )

    def test_an_overdue_report_is_a_major_finding(self):
        findings = report_currency_findings(4000.0, DEFAULT_REVALIDATION_DAYS, False)
        self.assertEqual(findings[0]["control"], "report-revalidation")
        self.assertEqual(findings[0]["severity"], "major")

    def test_a_formulation_change_voids_the_report(self):
        findings = report_currency_findings(10.0, DEFAULT_REVALIDATION_DAYS, True)
        self.assertEqual(findings[0]["control"], "formulation-change")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_the_change_flag_must_be_boolean(self):
        with self.assertRaises(ValueError):
            report_currency_findings(10.0, DEFAULT_REVALIDATION_DAYS, "no")


class DispositionTests(unittest.TestCase):
    def test_an_index_under_unity_with_clean_evidence_is_approved(self):
        self.assertEqual(
            selection_disposition([], 0.4, 1000.0, 500.0),
            "approved-for-crew-compartment",
        )

    def test_an_index_exactly_on_unity_is_approved(self):
        self.assertEqual(
            selection_disposition([], MAX_TOXICITY_INDEX, 500.0, 500.0),
            "approved-for-crew-compartment",
        )

    def test_an_over_index_material_becomes_a_mass_limit(self):
        self.assertEqual(
            selection_disposition([], 2.0, 250.0, 500.0),
            "approved-with-mass-limit",
        )

    def test_a_critical_finding_refuses_the_material_outright(self):
        findings = [{"severity": "critical", "control": "x", "detail": "y"}]
        self.assertEqual(selection_disposition(findings, 0.1, 1000.0, 500.0), "not-approved")

    def test_an_unbounded_limit_on_an_over_index_record_is_refused(self):
        self.assertEqual(
            selection_disposition([], 2.0, float("inf"), 500.0), "not-approved"
        )

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            selection_disposition([{"severity": "blocker"}], 0.1, 10.0, 1.0)


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_material_is_approved_for_the_compartment(self):
        result = assess_crewed_material_control(_spec())
        self.assertEqual(result["disposition"], "approved-for-crew-compartment")
        self.assertEqual(result["findings"], [])
        self.assertLess(result["toxicity_index"], MAX_TOXICITY_INDEX)

    def test_a_heavy_install_returns_the_mass_the_compartment_can_carry(self):
        result = assess_crewed_material_control(_spec(installed_mass_g=5000.0))
        self.assertEqual(result["disposition"], "approved-with-mass-limit")
        self.assertLess(result["mass_limit_g"], result["installed_mass_g"])
        records = compound_contributions(_compounds(), result["mass_limit_g"], 100.0)
        self.assertAlmostEqual(toxicity_index(records), MAX_TOXICITY_INDEX, places=9)

    def test_a_single_compound_over_its_own_allowable_becomes_a_mass_limit(self):
        hot = [{"name": "aldehyde-c", "yield_ug_per_g": 900.0, "smac_mg_m3": 0.1}]
        result = assess_crewed_material_control(_spec(compounds=hot))
        self.assertEqual(result["disposition"], "approved-with-mass-limit")
        controls = [f["control"] for f in result["findings"]]
        self.assertIn("single-compound-allowable", controls)
        self.assertEqual(result["binding_compound"][0], "aldehyde-c")

    def test_the_binding_compound_is_the_one_with_the_lowest_own_limit(self):
        result = assess_crewed_material_control(_spec())
        self.assertEqual(result["binding_compound"][0], "aldehyde-b")
        self.assertLess(result["mass_limit_g"], result["binding_compound"][1])

    def test_a_material_releasing_nothing_has_no_binding_compound(self):
        inert = [{"name": "inert-a", "yield_ug_per_g": 0.0, "smac_mg_m3": 10.0}]
        result = assess_crewed_material_control(_spec(compounds=inert))
        self.assertIsNone(result["binding_compound"])
        self.assertEqual(result["disposition"], "approved-for-crew-compartment")

    def test_binding_compound_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            binding_compound([], 100.0)

    def test_a_missing_offgassing_report_refuses_the_selection(self):
        held = [n for n in REQUIRED_EVIDENCE if n != "offgassing-test-report-70-29"]
        result = assess_crewed_material_control(_spec(evidence_held=held))
        self.assertEqual(result["disposition"], "not-approved")
        self.assertIn("offgassing-test-report-70-29", result["missing_evidence"])

    def test_a_missing_contamination_control_plan_is_major_not_fatal(self):
        held = [n for n in REQUIRED_EVIDENCE if n != "contamination-control-plan-70-01c"]
        result = assess_crewed_material_control(_spec(evidence_held=held))
        severities = {f["severity"] for f in result["findings"]}
        self.assertNotIn("critical", severities)
        self.assertIn("contamination-control-plan-70-01c", result["missing_evidence"])

    def test_a_reformulated_material_is_not_approved_on_the_old_report(self):
        result = assess_crewed_material_control(_spec(formulation_changed=True))
        self.assertEqual(result["disposition"], "not-approved")

    def test_findings_are_ranked_critical_first(self):
        result = assess_crewed_material_control(
            _spec(formulation_changed=True, days_since_test=9000.0)
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["free_volume_m3"]
        with self.assertRaises(ValueError):
            assess_crewed_material_control(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_crewed_material_control([_spec()])

    def test_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
