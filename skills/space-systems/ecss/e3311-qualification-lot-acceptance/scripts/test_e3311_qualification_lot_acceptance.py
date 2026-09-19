"""Contract tests for the clause 4.14.4 qualification and lot-acceptance logic."""

import unittest

from e3311_qualification_lot_acceptance_logic import (
    MAX_SAMPLE_SIZE,
    SNAP_TOLERANCE,
    acceptance_probability,
    assess_qualification_programme,
    attribute_sample_size,
    build_sample_plan,
    demonstrated_reliability,
    lot_homogeneity,
    lot_verdict,
    qualification_level,
    snap_to_integer,
    validate_count,
    validate_probability,
    zero_failure_sample_size,
)


def units(count=40, **overrides):
    base = {
        "explosive_batch": "B-771",
        "manufacturing_period": "2026-Q1",
        "build_standard": "rev-C",
    }
    base.update(overrides)
    return [dict(base, serial="SN-%03d" % i) for i in range(count)]


def good_spec(**overrides):
    spec = {
        "units": units(40),
        "reliability": 0.90,
        "confidence": 0.90,
        "allowed_failures": 0,
        "units_tested": 22,
        "observed_failures": 0,
        "acceptance_level": 20.0,
        "qualification_factor": 1.5,
        "declared_qualification_level": 30.0,
    }
    spec.update(overrides)
    return spec


class ProbabilityGuardTests(unittest.TestCase):
    def test_probability_returns_float(self):
        self.assertEqual(validate_probability("r", 0.5), 0.5)

    def test_one_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_probability("r", 1.0)

    def test_one_allowed_when_asked(self):
        self.assertEqual(validate_probability("p", 1.0, allow_one=True), 1.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability("r", 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability("r", True)

    def test_count_rejects_float(self):
        with self.assertRaises(ValueError):
            validate_count("n", 3.0)

    def test_count_rejects_below_minimum(self):
        with self.assertRaises(ValueError):
            validate_count("n", 0, minimum=1)


class SnapTests(unittest.TestCase):
    def test_near_integer_snaps(self):
        self.assertAlmostEqual(snap_to_integer(2.0 + SNAP_TOLERANCE / 100.0), 2.0, places=9)

    def test_genuine_fraction_is_left_alone(self):
        self.assertAlmostEqual(snap_to_integer(2.4), 2.4, places=9)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            snap_to_integer(float("inf"))


class SampleSizeTests(unittest.TestCase):
    def test_zero_failure_size_is_the_log_ratio_ceiling(self):
        self.assertEqual(zero_failure_sample_size(0.90, 0.90), 22)

    def test_exact_log_ratio_does_not_round_up_by_one(self):
        self.assertEqual(zero_failure_sample_size(0.5, 0.75), 2)

    def test_higher_confidence_needs_more_units(self):
        self.assertGreater(
            zero_failure_sample_size(0.99, 0.95), zero_failure_sample_size(0.99, 0.60)
        )

    def test_allowing_a_failure_enlarges_the_sample(self):
        zero = attribute_sample_size(0.90, 0.90, 0)
        one = attribute_sample_size(0.90, 0.90, 1)
        self.assertGreater(one, zero)

    def test_attribute_size_with_no_allowance_matches_the_zero_failure_form(self):
        self.assertEqual(
            attribute_sample_size(0.95, 0.90, 0), zero_failure_sample_size(0.95, 0.90)
        )

    def test_attribute_size_meets_its_own_consumer_risk(self):
        n = attribute_sample_size(0.90, 0.90, 1)
        risk = acceptance_probability(n, 1, 0.10)
        self.assertLessEqual(risk, 0.10 + SNAP_TOLERANCE)

    def test_sample_cap_is_a_real_bound(self):
        self.assertGreater(MAX_SAMPLE_SIZE, 1000)

    def test_reliability_of_one_rejected(self):
        with self.assertRaises(ValueError):
            zero_failure_sample_size(1.0, 0.90)


class AcceptanceProbabilityTests(unittest.TestCase):
    def test_a_perfect_lot_is_always_accepted(self):
        self.assertAlmostEqual(acceptance_probability(20, 0, 1e-12), 1.0, places=9)

    def test_probability_falls_as_the_defect_rate_rises(self):
        low = acceptance_probability(20, 0, 0.01)
        high = acceptance_probability(20, 0, 0.20)
        self.assertGreater(low, high)

    def test_allowance_equal_to_the_sample_accepts_everything(self):
        self.assertAlmostEqual(acceptance_probability(5, 5, 0.5), 1.0, places=9)

    def test_zero_allowance_is_the_survival_power(self):
        self.assertAlmostEqual(acceptance_probability(3, 0, 0.5), 0.125, places=9)


class DemonstratedReliabilityTests(unittest.TestCase):
    def test_a_single_unit_demonstrates_the_complement_of_confidence(self):
        self.assertAlmostEqual(demonstrated_reliability(1, 0.90), 0.10, places=9)

    def test_more_units_demonstrate_more_reliability(self):
        self.assertGreater(
            demonstrated_reliability(50, 0.90), demonstrated_reliability(10, 0.90)
        )

    def test_the_plan_size_reaches_its_target_reliability(self):
        n = zero_failure_sample_size(0.90, 0.90)
        self.assertGreaterEqual(demonstrated_reliability(n, 0.90), 0.90 - 1e-9)

    def test_zero_units_rejected(self):
        with self.assertRaises(ValueError):
            demonstrated_reliability(0, 0.90)


class QualificationLevelTests(unittest.TestCase):
    def test_level_scales_by_the_factor(self):
        self.assertAlmostEqual(qualification_level(20.0, 1.5), 30.0, places=9)

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            qualification_level(20.0, 0.8)

    def test_negative_acceptance_level_rejected(self):
        with self.assertRaises(ValueError):
            qualification_level(-3.0, 1.5)


class HomogeneityTests(unittest.TestCase):
    def test_one_batch_one_period_is_homogeneous(self):
        result = lot_homogeneity(units(10))
        self.assertTrue(result["homogeneous"])
        self.assertEqual(result["lot_size"], 10)

    def test_mixed_batches_are_a_finding(self):
        mixed = units(4) + units(4, explosive_batch="B-772")
        result = lot_homogeneity(mixed)
        self.assertFalse(result["homogeneous"])
        self.assertIn("explosive batches", result["findings"][0])

    def test_mixed_build_standards_are_a_finding(self):
        mixed = units(4) + units(4, build_standard="rev-D")
        result = lot_homogeneity(mixed)
        self.assertFalse(result["homogeneous"])

    def test_missing_field_rejected(self):
        bad = units(2)
        del bad[0]["manufacturing_period"]
        with self.assertRaises(ValueError):
            lot_homogeneity(bad)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            lot_homogeneity([])


class PlanAndVerdictTests(unittest.TestCase):
    def test_plan_fits_inside_a_large_lot(self):
        plan = build_sample_plan(40, 0.90, 0.90)
        self.assertTrue(plan["feasible"])
        self.assertEqual(plan["sample_size"], 22)

    def test_plan_larger_than_the_lot_is_infeasible(self):
        plan = build_sample_plan(5, 0.99, 0.95)
        self.assertFalse(plan["feasible"])
        self.assertIn("cannot demonstrate", plan["findings"][0])

    def test_clean_run_accepts_the_lot(self):
        plan = build_sample_plan(40, 0.90, 0.90)
        verdict = lot_verdict(plan, 22, 0)
        self.assertTrue(verdict["accepted"])
        self.assertTrue(verdict["plan_followed"])

    def test_short_run_is_a_finding_even_with_no_failures(self):
        plan = build_sample_plan(40, 0.90, 0.90)
        verdict = lot_verdict(plan, 10, 0)
        self.assertFalse(verdict["accepted"])
        self.assertFalse(verdict["plan_followed"])

    def test_failures_beyond_the_allowance_reject_the_lot(self):
        plan = build_sample_plan(40, 0.90, 0.90)
        verdict = lot_verdict(plan, 22, 1)
        self.assertFalse(verdict["accepted"])

    def test_more_failures_than_units_rejected(self):
        plan = build_sample_plan(40, 0.90, 0.90)
        with self.assertRaises(ValueError):
            lot_verdict(plan, 5, 6)

    def test_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            lot_verdict(["sample_size"], 5, 0)


class ProgrammeTests(unittest.TestCase):
    def test_clean_programme_qualifies(self):
        result = assess_qualification_programme(good_spec())
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["levels"]["required_level"], 30.0, places=9)

    def test_declared_level_below_the_requirement_is_a_finding(self):
        result = assess_qualification_programme(
            good_spec(declared_qualification_level=25.0)
        )
        self.assertFalse(result["qualified"])
        self.assertFalse(result["levels"]["adequate"])

    def test_declared_level_exactly_on_the_requirement_is_adequate(self):
        result = assess_qualification_programme(
            good_spec(declared_qualification_level=30.0)
        )
        self.assertTrue(result["levels"]["adequate"])
        self.assertAlmostEqual(result["levels"]["declared_level"], 30.0, places=9)

    def test_mixed_lot_sinks_the_programme(self):
        spec = good_spec(units=units(20) + units(20, explosive_batch="B-999"))
        result = assess_qualification_programme(spec)
        self.assertFalse(result["qualified"])

    def test_demonstrated_reliability_reported_for_a_clean_run(self):
        result = assess_qualification_programme(good_spec())
        self.assertIsNotNone(result["demonstrated_reliability"])
        self.assertGreaterEqual(result["demonstrated_reliability"], 0.90 - 1e-9)

    def test_no_demonstrated_reliability_when_a_unit_failed(self):
        result = assess_qualification_programme(good_spec(observed_failures=1))
        self.assertIsNone(result["demonstrated_reliability"])

    def test_missing_key_rejected(self):
        spec = good_spec()
        del spec["reliability"]
        with self.assertRaises(ValueError):
            assess_qualification_programme(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_programme(["units"])


if __name__ == "__main__":
    unittest.main()
