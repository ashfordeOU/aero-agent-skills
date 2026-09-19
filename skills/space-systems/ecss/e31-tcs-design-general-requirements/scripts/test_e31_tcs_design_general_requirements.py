"""Contract tests for the clause 4.4.1 thermal design-to-requirements logic."""

import unittest

from e31_tcs_design_general_requirements_logic import (
    MARGIN_TOLERANCE_K,
    MATURITY_UNCERTAINTY_K,
    acceptance_limit_c,
    assess_tcs_design,
    design_temperature_c,
    evaluate_item,
    qualification_limit_c,
    rank_design_drivers,
    requirement_margin_k,
    uncertainty_margin_k,
    validate_positive,
    validate_real,
    worst_case_basis_findings,
)


def item(**overrides):
    """Return a representative unit with a hot and a cold worst case."""
    record = {
        "name": "payload-electronics",
        "maturity": "detailed-correlated",
        "acceptance_margin_k": 5.0,
        "qualification_margin_k": 5.0,
        "cases": {
            "hot": {
                "predicted_c": 42.0,
                "requirement_c": 60.0,
                "environment": "maximum",
                "optical_properties": "end-of-life",
                "dissipation": "maximum",
            },
            "cold": {
                "predicted_c": -8.0,
                "requirement_c": -25.0,
                "environment": "minimum",
                "optical_properties": "beginning-of-life",
                "dissipation": "minimum",
            },
        },
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_real_accepts_negative(self):
        self.assertEqual(validate_real("x", -40), -40.0)

    def test_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            validate_real("x", True)

    def test_real_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            validate_real("x", float("nan"))

    def test_positive_rejects_zero_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_positive_allows_zero_when_asked(self):
        self.assertEqual(validate_positive("x", 0.0, allow_zero=True), 0.0)


class MaturityTests(unittest.TestCase):
    def test_preliminary_model_earns_the_widest_margin(self):
        self.assertAlmostEqual(uncertainty_margin_k("preliminary"), 15.0, places=12)

    def test_flight_correlated_model_earns_the_narrowest(self):
        self.assertAlmostEqual(uncertainty_margin_k("flight-correlated"), 3.0, places=12)

    def test_margins_narrow_as_maturity_rises(self):
        order = ["preliminary", "detailed-uncorrelated", "detailed-correlated",
                 "flight-correlated"]
        values = [MATURITY_UNCERTAINTY_K[name] for name in order]
        for index in range(1, len(values)):
            self.assertLess(values[index], values[index - 1])

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            uncertainty_margin_k("about-right")

    def test_non_string_maturity_rejected(self):
        with self.assertRaises(ValueError):
            uncertainty_margin_k(3)


class TemperatureStackTests(unittest.TestCase):
    def test_hot_design_temperature_adds_the_uncertainty(self):
        self.assertAlmostEqual(design_temperature_c(42.0, 5.0, "hot"), 47.0, places=12)

    def test_cold_design_temperature_subtracts_it(self):
        self.assertAlmostEqual(design_temperature_c(-8.0, 5.0, "cold"), -13.0, places=12)

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            design_temperature_c(42.0, 5.0, "worst")

    def test_hot_acceptance_limit_sits_above_the_design_value(self):
        self.assertAlmostEqual(acceptance_limit_c(47.0, 5.0, "hot"), 52.0, places=12)

    def test_cold_acceptance_limit_sits_below_it(self):
        self.assertAlmostEqual(acceptance_limit_c(-13.0, 5.0, "cold"), -18.0, places=12)

    def test_qualification_extends_the_acceptance_limit(self):
        self.assertAlmostEqual(
            qualification_limit_c(52.0, 5.0, "hot"), 57.0, places=12
        )

    def test_zero_acceptance_margin_allowed(self):
        self.assertAlmostEqual(acceptance_limit_c(47.0, 0.0, "hot"), 47.0, places=12)

    def test_negative_acceptance_margin_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_limit_c(47.0, -5.0, "hot")


class MarginTests(unittest.TestCase):
    def test_hot_margin_is_requirement_less_design(self):
        self.assertAlmostEqual(requirement_margin_k(47.0, 60.0, "hot"), 13.0, places=12)

    def test_cold_margin_is_design_less_requirement(self):
        self.assertAlmostEqual(
            requirement_margin_k(-13.0, -25.0, "cold"), 12.0, places=12
        )

    def test_margin_is_negative_when_the_limit_is_breached(self):
        self.assertAlmostEqual(requirement_margin_k(65.0, 60.0, "hot"), -5.0, places=12)

    def test_tolerance_is_a_rounding_allowance(self):
        self.assertLess(MARGIN_TOLERANCE_K, 1e-6)


class WorstCaseBasisTests(unittest.TestCase):
    def _case(self, **overrides):
        record = {
            "case": "hot",
            "environment": "maximum",
            "optical_properties": "end-of-life",
            "dissipation": "maximum",
        }
        record.update(overrides)
        return record

    def test_consistent_hot_case_has_no_findings(self):
        self.assertEqual(worst_case_basis_findings(self._case()), [])

    def test_consistent_cold_case_has_no_findings(self):
        cold = self._case(case="cold", environment="minimum",
                          optical_properties="beginning-of-life",
                          dissipation="minimum")
        self.assertEqual(worst_case_basis_findings(cold), [])

    def test_hot_case_with_beginning_of_life_properties_is_flagged(self):
        findings = worst_case_basis_findings(
            self._case(optical_properties="beginning-of-life")
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("optical properties", findings[0])

    def test_hot_case_with_minimum_dissipation_is_flagged(self):
        findings = worst_case_basis_findings(self._case(dissipation="minimum"))
        self.assertEqual(len(findings), 1)

    def test_a_fully_inverted_hot_case_raises_three_findings(self):
        findings = worst_case_basis_findings(
            self._case(environment="minimum",
                       optical_properties="beginning-of-life",
                       dissipation="minimum")
        )
        self.assertEqual(len(findings), 3)

    def test_unrecognised_environment_value_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_basis_findings(self._case(environment="nominal"))

    def test_missing_key_rejected(self):
        bad = self._case()
        del bad["dissipation"]
        with self.assertRaises(ValueError):
            worst_case_basis_findings(bad)


class EvaluateItemTests(unittest.TestCase):
    def test_nominal_item_is_compliant(self):
        record = evaluate_item(item())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_stack_is_built_from_the_uncertainty_margin(self):
        record = evaluate_item(item())
        self.assertAlmostEqual(record["uncertainty_margin_k"], 5.0, places=12)
        self.assertAlmostEqual(
            record["cases"]["hot"]["design_temperature_c"], 47.0, places=12
        )
        self.assertAlmostEqual(
            record["cases"]["hot"]["qualification_limit_c"], 57.0, places=12
        )

    def test_driving_case_is_the_smaller_margin(self):
        record = evaluate_item(item())
        self.assertEqual(record["driving_case"], "cold")
        self.assertAlmostEqual(record["smallest_margin_k"], 12.0, places=12)

    def test_a_coarser_model_erodes_both_margins(self):
        fine = evaluate_item(item())
        coarse = evaluate_item(item(maturity="preliminary"))
        self.assertAlmostEqual(
            fine["smallest_margin_k"] - coarse["smallest_margin_k"], 10.0, places=12
        )

    def test_margin_exactly_zero_is_accepted(self):
        record = item()
        record["cases"]["hot"]["requirement_c"] = 47.0
        evaluated = evaluate_item(record)
        self.assertAlmostEqual(
            evaluated["cases"]["hot"]["margin_k"], 0.0, places=9
        )
        self.assertTrue(evaluated["cases"]["hot"]["compliant"])

    def test_breached_hot_limit_raises_a_finding(self):
        record = item()
        record["cases"]["hot"]["requirement_c"] = 40.0
        evaluated = evaluate_item(record)
        self.assertFalse(evaluated["compliant"])
        self.assertTrue(any("misses its" in f for f in evaluated["findings"]))

    def test_inconsistent_basis_reaches_the_item_findings(self):
        record = item()
        record["cases"]["hot"]["dissipation"] = "minimum"
        evaluated = evaluate_item(record)
        self.assertFalse(evaluated["compliant"])
        self.assertTrue(any("worst case needs" in f for f in evaluated["findings"]))

    def test_item_without_both_cases_rejected(self):
        record = item()
        del record["cases"]["cold"]
        with self.assertRaises(ValueError):
            evaluate_item(record)

    def test_case_missing_a_key_rejected(self):
        record = item()
        del record["cases"]["cold"]["requirement_c"]
        with self.assertRaises(ValueError):
            evaluate_item(record)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_item("payload-electronics")


class RankingTests(unittest.TestCase):
    def test_ranking_puts_the_tightest_item_first(self):
        tight = evaluate_item(item(name="tight-unit", maturity="preliminary"))
        loose = evaluate_item(item(name="loose-unit"))
        ranked = rank_design_drivers([loose, tight])
        self.assertEqual(ranked[0]["name"], "tight-unit")

    def test_ties_break_on_the_name(self):
        first = evaluate_item(item(name="alpha-unit"))
        second = evaluate_item(item(name="beta-unit"))
        ranked = rank_design_drivers([second, first])
        self.assertEqual([r["name"] for r in ranked], ["alpha-unit", "beta-unit"])

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            rank_design_drivers([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            rank_design_drivers([{"name": "x"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"items": [item(), item(name="battery", maturity="preliminary")]}
        spec.update(overrides)
        return spec

    def test_nominal_assessment_is_compliant(self):
        result = assess_tcs_design(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_design_drivers_are_ordered_by_margin(self):
        result = assess_tcs_design(self._spec())
        self.assertEqual(result["design_drivers"][0]["name"], "battery")
        self.assertEqual(result["design_drivers"][0]["case"], "cold")

    def test_duplicate_names_are_a_traceability_finding(self):
        spec = self._spec(items=[item(), item()])
        result = assess_tcs_design(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("share a name" in f for f in result["findings"]))

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_tcs_design(self._spec(items=[]))

    def test_missing_items_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_tcs_design({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tcs_design(["items"])


if __name__ == "__main__":
    unittest.main()
