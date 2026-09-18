"""Contract tests for the offgassing facility, calibration and contamination controls."""

import unittest

from q7029_facility_and_analytical_control_logic import (
    BOUND_TOLERANCE,
    CHECK_STANDARD_BAND,
    MAX_BLANK_FRACTION,
    MAX_CARRYOVER_FRACTION,
    MAX_RESPONSE_FACTOR_SPREAD,
    MIN_CALIBRATION_POINTS,
    assess_facility_and_analytical_control,
    blank_fraction,
    calibration_findings,
    calibration_validity_fraction,
    carryover_fraction,
    check_standard_recovery,
    contamination_findings,
    net_of_blank,
    response_factor_spread,
    run_disposition,
)


def _curve(**over):
    base = {
        "response_factors": [1.00, 1.02, 0.99, 1.01, 1.00],
        "days_since_calibration": 12.0,
        "validity_days": 30.0,
        "check_standard_measured_ug": 98.0,
        "check_standard_nominal_ug": 100.0,
    }
    base.update(over)
    return base


def _run(**over):
    base = {
        "compounds": [
            {"name": "alcohol-a", "gross_ug": 400.0, "blank_ug": 8.0},
            {"name": "ketone-b", "gross_ug": 260.0, "blank_ug": 5.0},
        ],
        "quantitation_limit_ug": 20.0,
        "calibration": _curve(),
        "residue_ug": 1.0,
        "previous_gross_ug": 500.0,
        "chamber_cleaned": True,
    }
    base.update(over)
    return base


class BlankSubtractionTests(unittest.TestCase):
    def test_blank_fraction_is_the_quotient_of_blank_over_gross(self):
        self.assertAlmostEqual(blank_fraction(200.0, 20.0), 0.1, places=9)

    def test_a_zero_blank_is_a_valid_background(self):
        self.assertAlmostEqual(blank_fraction(200.0, 0.0), 0.0, places=9)

    def test_a_blank_above_the_gross_reports_a_fraction_above_one(self):
        self.assertGreater(blank_fraction(10.0, 40.0), 1.0)

    def test_non_positive_gross_rejected(self):
        with self.assertRaises(ValueError):
            blank_fraction(0.0, 1.0)

    def test_negative_blank_rejected(self):
        with self.assertRaises(ValueError):
            blank_fraction(100.0, -1.0)

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            blank_fraction(True, 0.5)

    def test_net_is_the_gross_less_the_blank(self):
        record = net_of_blank(400.0, 40.0, 10.0)
        self.assertAlmostEqual(record["net_ug"], 360.0, places=9)

    def test_a_blank_larger_than_the_gross_floors_the_net_at_zero(self):
        record = net_of_blank(30.0, 55.0, 10.0)
        self.assertAlmostEqual(record["net_ug"], 0.0, places=9)
        self.assertFalse(record["quantified"])

    def test_a_net_under_the_quantitation_limit_is_not_reported_as_a_number(self):
        record = net_of_blank(30.0, 22.0, 20.0)
        self.assertFalse(record["quantified"])
        self.assertAlmostEqual(record["reported_ug"], 0.0, places=9)

    def test_a_net_exactly_on_the_quantitation_limit_counts_as_quantified(self):
        record = net_of_blank(50.0, 30.0, 20.0)
        self.assertTrue(record["quantified"])
        self.assertAlmostEqual(record["reported_ug"], 20.0, places=9)

    def test_quantitation_limit_must_be_positive(self):
        with self.assertRaises(ValueError):
            net_of_blank(100.0, 1.0, 0.0)


class CalibrationTests(unittest.TestCase):
    def test_identical_response_factors_have_no_spread(self):
        self.assertAlmostEqual(response_factor_spread([2.0, 2.0, 2.0]), 0.0, places=9)

    def test_spread_is_relative_so_scaling_the_factors_does_not_change_it(self):
        small = response_factor_spread([1.0, 1.1, 0.9])
        large = response_factor_spread([100.0, 110.0, 90.0])
        self.assertAlmostEqual(small, large, places=9)

    def test_a_single_response_factor_is_not_a_curve(self):
        with self.assertRaises(ValueError):
            response_factor_spread([1.0])

    def test_a_non_positive_response_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            response_factor_spread([1.0, 0.0, 1.1])

    def test_validity_fraction_is_age_over_window(self):
        self.assertAlmostEqual(calibration_validity_fraction(15.0, 30.0), 0.5, places=9)

    def test_a_curve_used_on_its_last_valid_day_is_not_a_finding(self):
        curve = _curve(days_since_calibration=30.0, validity_days=30.0)
        controls = [f["control"] for f in calibration_findings(curve)]
        self.assertNotIn("calibration-validity", controls)

    def test_an_expired_curve_is_critical(self):
        curve = _curve(days_since_calibration=31.0, validity_days=30.0)
        finding = [f for f in calibration_findings(curve) if f["control"] == "calibration-validity"]
        self.assertEqual(len(finding), 1)
        self.assertEqual(finding[0]["severity"], "critical")

    def test_negative_calibration_age_rejected(self):
        with self.assertRaises(ValueError):
            calibration_validity_fraction(-1.0, 30.0)

    def test_recovery_is_measured_over_nominal(self):
        self.assertAlmostEqual(check_standard_recovery(95.0, 100.0), 0.95, places=9)

    def test_a_recovery_on_the_lower_band_edge_passes(self):
        low = CHECK_STANDARD_BAND[0]
        curve = _curve(check_standard_measured_ug=low * 100.0, check_standard_nominal_ug=100.0)
        controls = [f["control"] for f in calibration_findings(curve)]
        self.assertNotIn("check-standard-recovery", controls)

    def test_a_recovery_below_the_band_is_critical(self):
        curve = _curve(check_standard_measured_ug=70.0, check_standard_nominal_ug=100.0)
        finding = [f for f in calibration_findings(curve)
                   if f["control"] == "check-standard-recovery"]
        self.assertEqual(finding[0]["severity"], "critical")

    def test_a_short_curve_is_a_major_finding(self):
        curve = _curve(response_factors=[1.0, 1.01, 0.99])
        finding = [f for f in calibration_findings(curve) if f["control"] == "calibration-points"]
        self.assertEqual(finding[0]["severity"], "major")
        self.assertLess(3, MIN_CALIBRATION_POINTS)

    def test_a_wide_response_factor_spread_is_critical(self):
        curve = _curve(response_factors=[1.0, 2.0, 0.5, 1.8, 0.6])
        finding = [f for f in calibration_findings(curve)
                   if f["control"] == "response-factor-spread"]
        self.assertEqual(finding[0]["severity"], "critical")
        self.assertGreater(response_factor_spread(curve["response_factors"]),
                           MAX_RESPONSE_FACTOR_SPREAD)

    def test_a_clean_curve_raises_nothing(self):
        self.assertEqual(calibration_findings(_curve()), [])

    def test_missing_curve_key_rejected(self):
        curve = _curve()
        del curve["validity_days"]
        with self.assertRaises(ValueError):
            calibration_findings(curve)

    def test_curve_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            calibration_findings([_curve()])


class ContaminationTests(unittest.TestCase):
    def test_carryover_is_residue_over_the_previous_reading(self):
        self.assertAlmostEqual(carryover_fraction(5.0, 500.0), 0.01, places=9)

    def test_carryover_exactly_on_the_limit_is_not_a_finding(self):
        limit_residue = MAX_CARRYOVER_FRACTION * 500.0
        self.assertEqual(contamination_findings(limit_residue, 500.0, True), [])

    def test_carryover_above_the_limit_is_critical(self):
        findings = contamination_findings(50.0, 500.0, True)
        self.assertEqual(findings[0]["control"], "chamber-carryover")
        self.assertEqual(findings[0]["severity"], "critical")

    def test_an_uncleaned_chamber_is_a_major_finding(self):
        findings = contamination_findings(1.0, 500.0, False)
        self.assertEqual(findings[0]["control"], "chamber-cleaning")
        self.assertEqual(findings[0]["severity"], "major")

    def test_cleaning_flag_must_be_boolean(self):
        with self.assertRaises(ValueError):
            contamination_findings(1.0, 500.0, "yes")


class DispositionTests(unittest.TestCase):
    def test_no_findings_leave_the_run_valid(self):
        self.assertEqual(run_disposition([]), "run-valid")

    def test_a_major_finding_asks_for_actions(self):
        self.assertEqual(
            run_disposition([{"severity": "major", "control": "x", "detail": "y"}]),
            "run-valid-with-actions",
        )

    def test_a_critical_finding_invalidates_the_run(self):
        self.assertEqual(
            run_disposition([
                {"severity": "minor", "control": "x", "detail": "y"},
                {"severity": "critical", "control": "z", "detail": "w"},
            ]),
            "run-invalid",
        )

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            run_disposition([{"severity": "showstopper"}])


class AssessmentTests(unittest.TestCase):
    def test_a_controlled_run_is_valid_with_every_compound_quantified(self):
        result = assess_facility_and_analytical_control(_run())
        self.assertEqual(result["disposition"], "run-valid")
        self.assertEqual(result["findings"], [])
        self.assertEqual(sorted(result["quantified"]), ["alcohol-a", "ketone-b"])
        self.assertEqual(result["not_quantified"], [])

    def test_a_dominating_facility_blank_is_named_against_its_compound(self):
        run = _run(compounds=[{"name": "alcohol-a", "gross_ug": 100.0, "blank_ug": 40.0}])
        result = assess_facility_and_analytical_control(run)
        self.assertEqual(result["disposition"], "run-valid-with-actions")
        self.assertIn("alcohol-a", result["findings"][0]["detail"])
        self.assertGreater(result["compounds"][0]["blank_fraction"], MAX_BLANK_FRACTION)

    def test_a_blank_exactly_on_the_fraction_limit_is_accepted(self):
        run = _run(compounds=[{"name": "alcohol-a", "gross_ug": 100.0, "blank_ug": 10.0}])
        result = assess_facility_and_analytical_control(run)
        self.assertEqual(result["disposition"], "run-valid")
        self.assertAlmostEqual(
            result["compounds"][0]["blank_fraction"], MAX_BLANK_FRACTION, places=9
        )

    def test_a_compound_under_the_quantitation_limit_is_listed_not_zeroed_silently(self):
        run = _run(compounds=[{"name": "trace-c", "gross_ug": 25.0, "blank_ug": 8.0}])
        result = assess_facility_and_analytical_control(run)
        self.assertEqual(result["not_quantified"], ["trace-c"])
        self.assertEqual(result["quantified"], [])

    def test_findings_are_ranked_critical_first(self):
        run = _run(
            compounds=[{"name": "alcohol-a", "gross_ug": 100.0, "blank_ug": 40.0}],
            calibration=_curve(days_since_calibration=90.0),
        )
        result = assess_facility_and_analytical_control(run)
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")
        self.assertEqual(result["disposition"], "run-invalid")

    def test_an_empty_compound_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_facility_and_analytical_control(_run(compounds=[]))

    def test_a_compound_without_a_name_is_rejected(self):
        run = _run(compounds=[{"name": "   ", "gross_ug": 100.0, "blank_ug": 1.0}])
        with self.assertRaises(ValueError):
            assess_facility_and_analytical_control(run)

    def test_missing_run_key_rejected(self):
        run = _run()
        del run["residue_ug"]
        with self.assertRaises(ValueError):
            assess_facility_and_analytical_control(run)

    def test_run_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_facility_and_analytical_control([_run()])

    def test_bound_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
