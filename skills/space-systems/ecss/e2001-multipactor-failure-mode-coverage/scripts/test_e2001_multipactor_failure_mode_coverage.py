"""Contract test for the ECSS-E-ST-20-01C clause 4.3.1.3 coverage leaf.

Offline, deterministic, stdlib unittest. Run: python3 test_e2001_multipactor_failure_mode_coverage.py
"""

import math
import unittest

from e2001_multipactor_failure_mode_coverage_logic import (
    CREDIBILITY_STATES,
    FAILURE_CATEGORIES,
    MARGIN_TOLERANCE_DB,
    assess_failure_mode_coverage,
    breakdown_margin_db,
    derated_threshold_voltage,
    evaluate_failure_mode,
    governing_case,
    meets_required_margin,
    normalize_baseline,
    normalize_failure_mode,
    peak_gap_voltage,
    reflection_magnitude,
)

BASELINE = {
    "nominal_power_w": 100.0,
    "impedance_ohm": 50.0,
    "threshold_power_w": 1600.0,
    "critical": True,
}


def mode(**overrides):
    """A covered, credible degraded case that can be perturbed per test."""
    case = {
        "id": "fm-01",
        "category": "rf-power-redistribution",
        "credibility": "credible",
        "power_factor": 1.0,
        "in_design_cases": True,
        "in_verification_cases": True,
    }
    case.update(overrides)
    return case


class ReflectionTests(unittest.TestCase):
    def test_matched_load_reflects_nothing(self):
        self.assertAlmostEqual(reflection_magnitude(1.0), 0.0)

    def test_two_to_one_mismatch(self):
        self.assertAlmostEqual(reflection_magnitude(2.0), 1.0 / 3.0)

    def test_large_mismatch_approaches_unity(self):
        self.assertAlmostEqual(reflection_magnitude(99.0), 0.98)

    def test_ratio_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude(0.8)

    def test_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude(0.0)

    def test_non_numeric_ratio_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude("2.0")

    def test_boolean_ratio_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude(True)

    def test_infinite_ratio_rejected(self):
        with self.assertRaises(ValueError):
            reflection_magnitude(float("inf"))


class PeakVoltageTests(unittest.TestCase):
    def test_matched_peak_voltage(self):
        self.assertAlmostEqual(peak_gap_voltage(100.0, 50.0), 100.0)

    def test_mismatch_raises_peak_voltage(self):
        self.assertAlmostEqual(peak_gap_voltage(100.0, 50.0, 2.0), 100.0 * 4.0 / 3.0)

    def test_zero_power_is_permitted(self):
        self.assertAlmostEqual(peak_gap_voltage(0.0, 50.0), 0.0)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            peak_gap_voltage(-1.0, 50.0)

    def test_zero_impedance_rejected(self):
        with self.assertRaises(ValueError):
            peak_gap_voltage(100.0, 0.0)


class ThresholdVoltageTests(unittest.TestCase):
    def test_undereated_threshold_voltage(self):
        self.assertAlmostEqual(derated_threshold_voltage(1600.0, 50.0), 400.0)

    def test_derating_scales_threshold(self):
        self.assertAlmostEqual(derated_threshold_voltage(1600.0, 50.0, 0.5), 200.0)

    def test_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            derated_threshold_voltage(1600.0, 50.0, 1.2)

    def test_zero_factor_rejected(self):
        with self.assertRaises(ValueError):
            derated_threshold_voltage(1600.0, 50.0, 0.0)

    def test_zero_threshold_power_rejected(self):
        with self.assertRaises(ValueError):
            derated_threshold_voltage(0.0, 50.0)


class MarginTests(unittest.TestCase):
    def test_equal_voltages_give_zero_margin(self):
        self.assertAlmostEqual(breakdown_margin_db(100.0, 100.0), 0.0)

    def test_factor_of_two_is_six_db(self):
        self.assertAlmostEqual(breakdown_margin_db(100.0, 200.0), 6.0206, places=4)

    def test_applied_above_threshold_is_negative(self):
        self.assertLess(breakdown_margin_db(400.0, 200.0), 0.0)

    def test_zero_applied_voltage_rejected(self):
        with self.assertRaises(ValueError):
            breakdown_margin_db(0.0, 200.0)

    def test_exact_boundary_margin_is_met(self):
        required = 20.0 * math.log10(2.0)
        margin = breakdown_margin_db(100.0, 200.0)
        self.assertTrue(meets_required_margin(margin, required))

    def test_margin_a_hair_below_requirement_is_absorbed(self):
        required = 6.0
        self.assertTrue(meets_required_margin(required - MARGIN_TOLERANCE_DB / 2.0, required))

    def test_real_shortfall_is_not_absorbed(self):
        self.assertFalse(meets_required_margin(5.9, 6.0))

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            meets_required_margin("6.0", 6.0)

    def test_non_numeric_requirement_rejected(self):
        with self.assertRaises(ValueError):
            meets_required_margin(6.0, None)


class NormalizeBaselineTests(unittest.TestCase):
    def test_defaults_applied(self):
        base = normalize_baseline({"nominal_power_w": 10.0, "threshold_power_w": 100.0})
        self.assertAlmostEqual(base["impedance_ohm"], 50.0)
        self.assertAlmostEqual(base["nominal_vswr"], 1.0)
        self.assertTrue(base["critical"])

    def test_missing_nominal_power_rejected(self):
        with self.assertRaises(ValueError):
            normalize_baseline({"threshold_power_w": 100.0})

    def test_missing_threshold_power_rejected(self):
        with self.assertRaises(ValueError):
            normalize_baseline({"nominal_power_w": 10.0})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_baseline(["nominal_power_w", 10.0])

    def test_bad_nominal_vswr_rejected(self):
        with self.assertRaises(ValueError):
            normalize_baseline(
                {"nominal_power_w": 10.0, "threshold_power_w": 100.0, "nominal_vswr": 0.5}
            )


class NormalizeFailureModeTests(unittest.TestCase):
    def test_defaults_are_uncovered(self):
        case = normalize_failure_mode({"id": "fm-x", "category": "thermal-excursion"})
        self.assertFalse(case["in_design_cases"])
        self.assertFalse(case["in_verification_cases"])
        self.assertEqual(case["credibility"], "credible")
        self.assertAlmostEqual(case["power_factor"], 1.0)

    def test_every_known_category_normalizes(self):
        for category in FAILURE_CATEGORIES:
            case = normalize_failure_mode({"id": "fm-" + category, "category": category})
            self.assertEqual(case["category"], category)

    def test_every_credibility_state_normalizes(self):
        for state in CREDIBILITY_STATES:
            case = normalize_failure_mode(
                {
                    "id": "fm-" + state,
                    "category": "pressure-transient",
                    "credibility": state,
                    "justification": "bounded by the vent-path analysis",
                }
            )
            self.assertEqual(case["credibility"], state)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode({"id": "fm-x", "category": "solar-flare"})

    def test_unknown_credibility_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode(
                {"id": "fm-x", "category": "thermal-excursion", "credibility": "maybe"}
            )

    def test_empty_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode({"id": "  ", "category": "thermal-excursion"})

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode({"category": "thermal-excursion"})

    def test_zero_power_factor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode(
                {"id": "fm-x", "category": "thermal-excursion", "power_factor": 0.0}
            )

    def test_negative_power_factor_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode(
                {"id": "fm-x", "category": "thermal-excursion", "power_factor": -2.0}
            )

    def test_threshold_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode(
                {"id": "fm-x", "category": "thermal-excursion", "threshold_factor": 1.1}
            )

    def test_non_string_justification_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode(
                {"id": "fm-x", "category": "thermal-excursion", "justification": 7}
            )

    def test_non_mapping_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_failure_mode("fm-x")


class EvaluateFailureModeTests(unittest.TestCase):
    def test_nominal_case_margin(self):
        case = evaluate_failure_mode(mode(), BASELINE, 6.0)
        self.assertAlmostEqual(case["applied_voltage_v"], 100.0)
        self.assertAlmostEqual(case["threshold_voltage_v"], 400.0)
        self.assertAlmostEqual(case["margin_db"], 12.0412, places=4)
        self.assertEqual(case["findings"], [])

    def test_power_redistribution_halves_the_margin_in_db(self):
        case = evaluate_failure_mode(mode(power_factor=4.0), BASELINE, 6.0)
        self.assertAlmostEqual(case["applied_power_w"], 400.0)
        self.assertAlmostEqual(case["margin_db"], 6.0206, places=4)
        self.assertTrue(case["meets_required_margin"])

    def test_mismatch_case_uses_the_worse_of_the_two_ratios(self):
        case = evaluate_failure_mode(
            mode(category="impedance-mismatch", vswr=2.0),
            dict(BASELINE, nominal_vswr=1.5),
            6.0,
        )
        self.assertAlmostEqual(case["applied_vswr"], 2.0)
        self.assertAlmostEqual(case["applied_voltage_v"], 100.0 * 4.0 / 3.0)

    def test_baseline_mismatch_wins_when_it_is_worse(self):
        case = evaluate_failure_mode(mode(vswr=1.1), dict(BASELINE, nominal_vswr=2.0), 6.0)
        self.assertAlmostEqual(case["applied_vswr"], 2.0)

    def test_threshold_derating_lowers_the_margin(self):
        case = evaluate_failure_mode(
            mode(category="thermal-excursion", threshold_factor=0.5), BASELINE, 6.0
        )
        self.assertAlmostEqual(case["threshold_voltage_v"], 200.0)
        self.assertAlmostEqual(case["margin_db"], 6.0206, places=4)

    def test_margin_shortfall_is_a_finding(self):
        case = evaluate_failure_mode(mode(power_factor=16.0), BASELINE, 6.0)
        self.assertIn("margin-shortfall", case["findings"])
        self.assertFalse(case["meets_required_margin"])

    def test_credible_case_absent_from_design_set(self):
        case = evaluate_failure_mode(mode(in_design_cases=False), BASELINE, 6.0)
        self.assertIn("design-case-missing", case["findings"])

    def test_critical_unit_needs_the_verification_case(self):
        case = evaluate_failure_mode(mode(in_verification_cases=False), BASELINE, 6.0)
        self.assertIn("verification-case-missing", case["findings"])

    def test_non_critical_unit_needs_only_the_design_case(self):
        case = evaluate_failure_mode(
            mode(in_verification_cases=False), dict(BASELINE, critical=False), 6.0
        )
        self.assertEqual(case["findings"], [])

    def test_non_credible_case_needs_a_justification(self):
        case = evaluate_failure_mode(
            mode(credibility="non-credible", in_design_cases=False), BASELINE, 6.0
        )
        self.assertEqual(case["findings"], ["credibility-justification-missing"])

    def test_justified_non_credible_case_is_clean(self):
        case = evaluate_failure_mode(
            mode(
                credibility="non-credible",
                in_design_cases=False,
                in_verification_cases=False,
                justification="two independent commands are needed to reach it",
            ),
            BASELINE,
            6.0,
        )
        self.assertEqual(case["findings"], [])

    def test_non_finite_requirement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_failure_mode(mode(), BASELINE, float("nan"))


class GoverningCaseTests(unittest.TestCase):
    def test_least_margin_governs(self):
        cases = [
            evaluate_failure_mode(mode(id="fm-a", power_factor=1.0), BASELINE, 6.0),
            evaluate_failure_mode(mode(id="fm-b", power_factor=4.0), BASELINE, 6.0),
        ]
        self.assertEqual(governing_case(cases)["id"], "fm-b")

    def test_non_credible_cases_never_govern(self):
        cases = [
            evaluate_failure_mode(
                mode(
                    id="fm-a",
                    power_factor=16.0,
                    credibility="non-credible",
                    justification="single-point command inhibited",
                ),
                BASELINE,
                6.0,
            ),
            evaluate_failure_mode(mode(id="fm-b", power_factor=4.0), BASELINE, 6.0),
        ]
        self.assertEqual(governing_case(cases)["id"], "fm-b")

    def test_no_credible_case_returns_none(self):
        cases = [
            evaluate_failure_mode(
                mode(id="fm-a", credibility="non-credible", justification="bounded"),
                BASELINE,
                6.0,
            )
        ]
        self.assertIsNone(governing_case(cases))

    def test_tie_is_broken_by_identifier(self):
        cases = [
            evaluate_failure_mode(mode(id="fm-z"), BASELINE, 6.0),
            evaluate_failure_mode(mode(id="fm-a"), BASELINE, 6.0),
        ]
        self.assertEqual(governing_case(cases)["id"], "fm-a")


class CoverageAuditTests(unittest.TestCase):
    def test_fully_covered_set_is_compliant(self):
        report = assess_failure_mode_coverage(
            [mode(id="fm-a"), mode(id="fm-b", power_factor=2.0)], BASELINE, 6.0
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["credible_case_count"], 2)
        self.assertEqual(report["governing_case_id"], "fm-b")

    def test_uncovered_case_makes_the_set_non_compliant(self):
        report = assess_failure_mode_coverage(
            [mode(id="fm-a"), mode(id="fm-b", in_design_cases=False)], BASELINE, 6.0
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(
            report["findings"], [{"id": "fm-b", "finding": "design-case-missing"}]
        )

    def test_governing_margin_is_reported(self):
        report = assess_failure_mode_coverage(
            [mode(id="fm-a"), mode(id="fm-b", power_factor=4.0)], BASELINE, 6.0
        )
        self.assertAlmostEqual(report["governing_margin_db"], 6.0206, places=4)

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode_coverage([mode(), mode()], BASELINE, 6.0)

    def test_empty_case_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode_coverage([], BASELINE, 6.0)

    def test_non_sequence_case_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_failure_mode_coverage({"id": "fm-a"}, BASELINE, 6.0)

    def test_report_echoes_the_requirement_and_criticality(self):
        report = assess_failure_mode_coverage([mode()], dict(BASELINE, critical=False), 8.0)
        self.assertAlmostEqual(report["required_margin_db"], 8.0)
        self.assertFalse(report["critical"])


if __name__ == "__main__":
    unittest.main()
