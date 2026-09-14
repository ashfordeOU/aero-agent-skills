"""Contract tests for the clause 4.3.8 radiation verification logic."""

import unittest

from q6013_class_1_radiation_verification_testing_logic import (
    DOSE_SENSITIVE_FAMILIES,
    MIN_RVT_SAMPLE,
    achieved_margin,
    assess_radiation_verification,
    evaluate_single_event_threshold,
    is_dose_sensitive_family,
    lot_capability_krad,
    margin_meets_requirement,
    required_capability_krad,
    validate_dose_krad,
    validate_sample,
    verification_test_required,
)


def ladder(*pairs):
    """Build an irradiation ladder from (dose, tested, within-limits) triples."""
    return [
        {"dose_krad": d, "units_tested": t, "units_within_limits": w}
        for d, t, w in pairs
    ]


class DoseValidationTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertEqual(validate_dose_krad(30, "d"), 30.0)

    def test_zero_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_krad(0.0, "d")

    def test_negative_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_krad(-5.0, "d")

    def test_non_numeric_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_krad("30", "d")

    def test_boolean_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_krad(True, "d")

    def test_non_finite_dose_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_krad(float("nan"), "d")


class RequiredCapabilityTests(unittest.TestCase):
    def test_capability_is_dose_times_margin(self):
        self.assertAlmostEqual(required_capability_krad(30.0, 2.0), 60.0, places=9)

    def test_unity_margin_is_the_mission_dose(self):
        self.assertAlmostEqual(required_capability_krad(12.5, 1.0), 12.5, places=9)

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_capability_krad(30.0, 0.9)

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            required_capability_krad(30.0, "2")


class FamilySensitivityTests(unittest.TestCase):
    def test_known_sensitive_family(self):
        self.assertTrue(is_dose_sensitive_family("bipolar-linear"))

    def test_case_and_padding_tolerated(self):
        self.assertTrue(is_dose_sensitive_family("  Optocoupler  "))

    def test_family_outside_the_set(self):
        self.assertFalse(is_dose_sensitive_family("passive-film-resistor"))

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            is_dose_sensitive_family("   ")

    def test_sensitive_set_is_immutable(self):
        self.assertIsInstance(DOSE_SENSITIVE_FAMILIES, frozenset)


class TestRequiredDecisionTests(unittest.TestCase):
    def _part(self, **over):
        part = {
            "family": "cmos-digital",
            "required_capability_krad": 60.0,
            "declared_capability_krad": 100.0,
            "declared_from_flight_lot": True,
        }
        part.update(over)
        return part

    def test_flight_lot_evidence_covering_requirement_needs_no_test(self):
        self.assertFalse(verification_test_required(self._part())["required"])

    def test_missing_declared_capability_forces_a_test(self):
        out = verification_test_required(self._part(declared_capability_krad=None))
        self.assertTrue(out["required"])
        self.assertIn("no declared radiation capability for the part", out["reasons"])

    def test_capability_below_requirement_forces_a_test(self):
        out = verification_test_required(self._part(declared_capability_krad=40.0))
        self.assertTrue(out["required"])

    def test_sensitive_family_cannot_inherit_another_lots_capability(self):
        out = verification_test_required(self._part(declared_from_flight_lot=False))
        self.assertTrue(out["required"])

    def test_insensitive_family_may_inherit_a_covering_capability(self):
        out = verification_test_required(
            self._part(family="passive-film-resistor", declared_from_flight_lot=False)
        )
        self.assertFalse(out["required"])

    def test_capability_exactly_at_the_requirement_is_covered(self):
        part = self._part(declared_capability_krad=60.0)
        self.assertAlmostEqual(part["declared_capability_krad"], 60.0, places=9)
        self.assertFalse(verification_test_required(part)["required"])

    def test_missing_key_rejected(self):
        part = self._part()
        del part["family"]
        with self.assertRaises(ValueError):
            verification_test_required(part)

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            verification_test_required(["cmos-digital"])

    def test_non_boolean_traceability_rejected(self):
        with self.assertRaises(ValueError):
            verification_test_required(self._part(declared_from_flight_lot="yes"))


class SampleValidationTests(unittest.TestCase):
    def test_compliant_sample_has_no_findings(self):
        out = validate_sample(5, 400, True)
        self.assertTrue(out["acceptable"])
        self.assertEqual(out["findings"], [])

    def test_sample_below_the_floor_is_a_finding(self):
        out = validate_sample(2, 400, True)
        self.assertFalse(out["acceptable"])
        self.assertEqual(len(out["findings"]), 1)

    def test_sample_outside_the_flight_lot_is_a_finding(self):
        out = validate_sample(5, 400, False)
        self.assertFalse(out["acceptable"])

    def test_both_defects_reported_together(self):
        out = validate_sample(1, 400, False)
        self.assertEqual(len(out["findings"]), 2)

    def test_default_floor_is_exposed(self):
        self.assertEqual(validate_sample(5, 400, True)["minimum"], MIN_RVT_SAMPLE)

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(50, 10, True)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(0, 400, True)

    def test_float_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(5.0, 400, True)


class LotCapabilityTests(unittest.TestCase):
    def test_capability_is_the_last_fully_passing_step(self):
        steps = ladder((10.0, 4, 4), (30.0, 4, 4), (50.0, 4, 3))
        self.assertAlmostEqual(lot_capability_krad(steps), 30.0, places=9)

    def test_all_steps_passing_gives_the_top_step(self):
        steps = ladder((10.0, 4, 4), (30.0, 4, 4), (100.0, 4, 4))
        self.assertAlmostEqual(lot_capability_krad(steps), 100.0, places=9)

    def test_failure_at_the_first_step_gives_zero(self):
        steps = ladder((10.0, 4, 2), (30.0, 4, 4))
        self.assertAlmostEqual(lot_capability_krad(steps), 0.0, places=9)

    def test_a_recovery_above_a_failed_step_is_not_credited(self):
        steps = ladder((10.0, 4, 4), (30.0, 4, 1), (50.0, 4, 4))
        self.assertAlmostEqual(lot_capability_krad(steps), 10.0, places=9)

    def test_unordered_ladder_rejected(self):
        with self.assertRaises(ValueError):
            lot_capability_krad(ladder((30.0, 4, 4), (10.0, 4, 4)))

    def test_repeated_dose_rejected(self):
        with self.assertRaises(ValueError):
            lot_capability_krad(ladder((30.0, 4, 4), (30.0, 4, 4)))

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            lot_capability_krad([])

    def test_more_passing_than_tested_rejected(self):
        with self.assertRaises(ValueError):
            lot_capability_krad(ladder((30.0, 4, 5)))

    def test_missing_step_key_rejected(self):
        with self.assertRaises(ValueError):
            lot_capability_krad([{"dose_krad": 30.0, "units_tested": 4}])


class MarginTests(unittest.TestCase):
    def test_margin_is_capability_over_mission_dose(self):
        self.assertAlmostEqual(achieved_margin(60.0, 30.0), 2.0, places=9)

    def test_zero_capability_gives_zero_margin(self):
        self.assertAlmostEqual(achieved_margin(0.0, 30.0), 0.0, places=9)

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            achieved_margin(-1.0, 30.0)

    def test_margin_above_requirement_passes(self):
        self.assertTrue(margin_meets_requirement(2.5, 2.0))

    def test_margin_exactly_at_requirement_passes(self):
        value = achieved_margin(60.0, 30.0)
        self.assertAlmostEqual(value, 2.0, places=9)
        self.assertTrue(margin_meets_requirement(value, 2.0))

    def test_margin_below_requirement_fails(self):
        self.assertFalse(margin_meets_requirement(1.5, 2.0))


class SingleEventTests(unittest.TestCase):
    def test_threshold_above_requirement_is_compliant(self):
        out = evaluate_single_event_threshold(60.0, 37.0)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_threshold_at_the_requirement_is_compliant(self):
        out = evaluate_single_event_threshold(37.0, 37.0)
        self.assertAlmostEqual(out["measured_let"], out["required_let"], places=9)
        self.assertTrue(out["compliant"])

    def test_threshold_below_requirement_raises_a_finding(self):
        out = evaluate_single_event_threshold(15.0, 37.0)
        self.assertFalse(out["compliant"])
        self.assertEqual(len(out["findings"]), 1)

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_single_event_threshold(0.0, 37.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "family": "bipolar-linear",
            "mission_dose_krad": 20.0,
            "required_margin": 2.0,
            "lot_size": 500,
            "sample_size": 6,
            "sample_from_flight_lot": True,
            "dose_steps": ladder((10.0, 6, 6), (20.0, 6, 6), (50.0, 6, 6)),
        }
        spec.update(over)
        return spec

    def test_verified_lot_is_compliant(self):
        out = assess_radiation_verification(self._spec())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["disposition"], "lot-verified")
        self.assertEqual(out["findings"], [])

    def test_required_capability_is_reported(self):
        out = assess_radiation_verification(self._spec())
        self.assertAlmostEqual(out["required_capability_krad"], 40.0, places=9)

    def test_capability_exactly_at_the_required_margin_passes(self):
        out = assess_radiation_verification(
            self._spec(dose_steps=ladder((10.0, 6, 6), (40.0, 6, 6), (60.0, 6, 2)))
        )
        self.assertAlmostEqual(out["achieved_margin"], 2.0, places=9)
        self.assertTrue(out["margin_compliant"])

    def test_short_capability_rejects_the_lot(self):
        out = assess_radiation_verification(
            self._spec(dose_steps=ladder((10.0, 6, 6), (20.0, 6, 3)))
        )
        self.assertFalse(out["compliant"])
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_sample_defect_invalidates_the_evidence(self):
        out = assess_radiation_verification(self._spec(sample_from_flight_lot=False))
        self.assertEqual(out["disposition"], "verification-evidence-invalid")

    def test_single_event_shortfall_is_reported(self):
        out = assess_radiation_verification(
            self._spec(measured_let=12.0, required_let=37.0)
        )
        self.assertFalse(out["compliant"])
        self.assertEqual(len(out["findings"]), 1)

    def test_required_let_without_a_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification(self._spec(required_let=37.0))

    def test_test_requirement_decision_travels_with_the_result(self):
        out = assess_radiation_verification(self._spec())
        self.assertTrue(out["test_required"])
        self.assertTrue(out["test_required_reasons"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["dose_steps"]
        with self.assertRaises(ValueError):
            assess_radiation_verification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiation_verification(["family"])

    def test_margin_scales_with_the_mission_dose(self):
        low = assess_radiation_verification(self._spec(mission_dose_krad=10.0))
        high = assess_radiation_verification(self._spec(mission_dose_krad=20.0))
        self.assertAlmostEqual(
            low["achieved_margin"], 2.0 * high["achieved_margin"], places=9
        )


if __name__ == "__main__":
    unittest.main()
