"""Contract test for the motorization-uncertainty leaf (stdlib unittest)."""

import unittest

from e3301_motorization_factors_uncertainty_logic import (
    MIN_FACTOR_BY_KIND,
    UPLIFT_BY_BASIS,
    VALID_LIFE_POINTS,
    applied_uncertainty_factor,
    assess_contribution,
    assess_motorization_uncertainty,
    factored_value,
    life_coverage_findings,
    minimum_uncertainty_factor,
    travel_coverage_findings,
    validate_contribution,
)

BOTH_LIFE_POINTS = list(VALID_LIFE_POINTS)


def contribution(cid="C-1", kind="dry-friction", **kw):
    record = {
        "id": cid,
        "kind": kind,
        "basis": "measured-on-flight-standard-hardware",
        "nominal_value": 0.20,
        "life_points": BOTH_LIFE_POINTS,
        "worst_case_over_travel": True,
    }
    record.update(kw)
    return record


def function_record(**kw):
    record = {
        "id": "HDRM-HINGE-DRIVE",
        "units": "torque-nm",
        "travel_range": 90.0,
        "required_life_points": BOTH_LIFE_POINTS,
        "contributions": [
            contribution("C-1", "dry-friction", nominal_value=0.20),
            contribution("C-2", "harness-cable-resistance", nominal_value=0.10),
            contribution("C-3", "inertia", nominal_value=0.05),
        ],
    }
    record.update(kw)
    return record


class TestMinimumFactor(unittest.TestCase):
    def test_flight_standard_measurement_carries_the_bare_kind_floor(self):
        value = minimum_uncertainty_factor(
            "dry-friction", "measured-on-flight-standard-hardware"
        )
        self.assertAlmostEqual(value, MIN_FACTOR_BY_KIND["dry-friction"], places=9)

    def test_heritage_estimate_is_uplifted_above_the_kind_floor(self):
        measured = minimum_uncertainty_factor(
            "lubricated-friction", "measured-on-flight-standard-hardware"
        )
        estimated = minimum_uncertainty_factor(
            "lubricated-friction", "estimated-from-heritage"
        )
        self.assertAlmostEqual(
            estimated,
            measured * UPLIFT_BY_BASIS["estimated-from-heritage"],
            places=9,
        )

    def test_friction_carries_more_than_inertia(self):
        basis = "measured-on-flight-standard-hardware"
        self.assertGreater(
            minimum_uncertainty_factor("dry-friction", basis),
            minimum_uncertainty_factor("inertia", basis),
        )

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            minimum_uncertainty_factor("gremlins", "estimated-from-heritage")

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            minimum_uncertainty_factor("dry-friction", "someone-said-so")


class TestValidateContribution(unittest.TestCase):
    def test_travel_stations_are_sorted(self):
        norm = validate_contribution(
            contribution(worst_case_over_travel=False, travel_stations=[90.0, 0.0, 45.0])
        )
        self.assertEqual(norm["travel_stations"], [0.0, 45.0, 90.0])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(["C-1"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution(""))

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution("C-1", kind="magic"))

    def test_negative_nominal_value_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution("C-1", nominal_value=-0.1))

    def test_declared_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution("C-1", declared_factor=0.8))

    def test_unknown_life_point_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution("C-1", life_points=["mid-life-crisis"]))

    def test_non_boolean_worst_case_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_contribution(contribution("C-1", worst_case_over_travel="yes"))


class TestAppliedFactor(unittest.TestCase):
    def test_absent_declared_factor_falls_to_the_minimum(self):
        factor, findings = applied_uncertainty_factor(contribution())
        self.assertAlmostEqual(factor, MIN_FACTOR_BY_KIND["dry-friction"], places=9)
        self.assertEqual(findings, [])

    def test_declared_factor_on_the_minimum_is_accepted(self):
        floor = minimum_uncertainty_factor(
            "dry-friction", "measured-on-flight-standard-hardware"
        )
        factor, findings = applied_uncertainty_factor(
            contribution(declared_factor=floor)
        )
        self.assertAlmostEqual(factor, floor, places=9)
        self.assertEqual(findings, [])

    def test_declared_factor_below_the_minimum_is_raised_and_flagged(self):
        factor, findings = applied_uncertainty_factor(
            contribution(declared_factor=1.5)
        )
        self.assertAlmostEqual(factor, MIN_FACTOR_BY_KIND["dry-friction"], places=9)
        self.assertEqual(findings, ["declared-factor-below-minimum"])

    def test_declared_factor_above_the_minimum_is_kept(self):
        factor, findings = applied_uncertainty_factor(
            contribution(declared_factor=4.0)
        )
        self.assertAlmostEqual(factor, 4.0, places=9)
        self.assertEqual(findings, [])

    def test_factored_value_uses_the_applied_factor(self):
        value = factored_value(contribution(nominal_value=0.2, declared_factor=4.0))
        self.assertAlmostEqual(value, 0.8, places=9)


class TestCoverage(unittest.TestCase):
    def test_worst_case_flag_covers_the_travel(self):
        self.assertEqual(travel_coverage_findings(contribution(), 90.0), [])

    def test_no_stations_and_no_flag_is_a_finding(self):
        findings = travel_coverage_findings(
            contribution(worst_case_over_travel=False), 90.0
        )
        self.assertEqual(findings, ["travel-coverage-not-declared"])

    def test_wide_gap_between_stations_is_a_finding(self):
        findings = travel_coverage_findings(
            contribution(worst_case_over_travel=False, travel_stations=[0.0, 90.0]),
            90.0,
        )
        self.assertIn("travel-gap-wider-than-allowed", findings)

    def test_stations_stopping_short_of_the_end_are_a_finding(self):
        stations = [float(x) for x in range(0, 50, 5)]
        findings = travel_coverage_findings(
            contribution(worst_case_over_travel=False, travel_stations=stations), 90.0
        )
        self.assertIn("travel-end-not-covered", findings)

    def test_dense_station_schedule_covers_the_travel(self):
        stations = [float(x) for x in range(0, 91, 5)]
        findings = travel_coverage_findings(
            contribution(worst_case_over_travel=False, travel_stations=stations), 90.0
        )
        self.assertEqual(findings, [])

    def test_zero_travel_range_raises(self):
        with self.assertRaises(ValueError):
            travel_coverage_findings(contribution(), 0.0)

    def test_missing_end_of_life_is_a_finding(self):
        findings = life_coverage_findings(
            contribution(life_points=["begin-of-life"]), BOTH_LIFE_POINTS
        )
        self.assertEqual(findings, ["not-evaluated-at:end-of-life"])

    def test_empty_required_life_points_raises(self):
        with self.assertRaises(ValueError):
            life_coverage_findings(contribution(), [])


class TestAssessFunction(unittest.TestCase):
    def test_clean_function_passes(self):
        report = assess_motorization_uncertainty(function_record())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], [])

    def test_factored_total_is_the_sum_of_factored_contributions(self):
        report = assess_motorization_uncertainty(function_record())
        expected = (
            0.20 * MIN_FACTOR_BY_KIND["dry-friction"]
            + 0.10 * MIN_FACTOR_BY_KIND["harness-cable-resistance"]
            + 0.05 * MIN_FACTOR_BY_KIND["inertia"]
        )
        self.assertAlmostEqual(report["factored_total"], expected, places=9)

    def test_uncertainty_allowance_is_the_difference_from_nominal(self):
        report = assess_motorization_uncertainty(function_record())
        self.assertAlmostEqual(
            report["uncertainty_allowance"],
            report["factored_total"] - report["nominal_total"],
            places=9,
        )

    def test_per_contribution_factoring_is_not_a_single_scale_on_the_sum(self):
        report = assess_motorization_uncertainty(function_record())
        single_scale = report["nominal_total"] * MIN_FACTOR_BY_KIND["inertia"]
        self.assertGreater(report["factored_total"], single_scale)

    def test_dominant_contribution_is_named(self):
        report = assess_motorization_uncertainty(function_record())
        self.assertEqual(report["dominant_contribution_id"], "C-1")

    def test_a_contribution_missing_end_of_life_fails_the_function(self):
        record = function_record()
        record["contributions"][1] = contribution(
            "C-2", "harness-cable-resistance", life_points=["begin-of-life"]
        )
        report = assess_motorization_uncertainty(record)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["C-2"])

    def test_duplicate_contribution_id_raises(self):
        record = function_record(
            contributions=[contribution("C-1"), contribution("C-1")]
        )
        with self.assertRaises(ValueError):
            assess_motorization_uncertainty(record)

    def test_empty_contribution_list_raises(self):
        with self.assertRaises(ValueError):
            assess_motorization_uncertainty(function_record(contributions=[]))

    def test_unknown_units_raise(self):
        with self.assertRaises(ValueError):
            assess_motorization_uncertainty(function_record(units="furlongs"))

    def test_zero_travel_range_raises(self):
        with self.assertRaises(ValueError):
            assess_motorization_uncertainty(function_record(travel_range=0.0))

    def test_assess_contribution_reports_the_minimum_and_the_applied_factor(self):
        result = assess_contribution(
            contribution(declared_factor=1.2), 90.0, BOTH_LIFE_POINTS
        )
        self.assertAlmostEqual(
            result["minimum_factor"], MIN_FACTOR_BY_KIND["dry-friction"], places=9
        )
        self.assertAlmostEqual(
            result["applied_factor"], MIN_FACTOR_BY_KIND["dry-friction"], places=9
        )
        self.assertIn("declared-factor-below-minimum", result["findings"])


if __name__ == "__main__":
    unittest.main()
