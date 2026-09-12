import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_experimental_logic import (
    AssessmentError,
    DEFAULT_MODEL_UNCERTAINTY_PCT,
    MAX_SUPERSEDE_UNCERTAINTY_PCT,
    MAX_OFFSET_FOR_SUPERSEDE_PCT,
    assess_supersedes_model,
    check_provenance,
    compute_combined_assessment,
    compute_offset_pct,
    run_background_assessment,
    validate_experimental_record,
    validate_reference_record,
)


def _make_exp(
    particle_type="proton",
    quantity="flux",
    value=1000.0,
    uncertainty_pct=10.0,
    duration_s=3600.0,
    quality_flag="valid",
    source="ICARE-NG",
    provenance="PROBA-V ICARE-NG dataset v2.1",
):
    return {
        "source": source,
        "particle_type": particle_type,
        "quantity": quantity,
        "value": value,
        "uncertainty_pct": uncertainty_pct,
        "duration_s": duration_s,
        "quality_flag": quality_flag,
        "provenance": provenance,
    }


def _make_ref(
    particle_type="proton",
    quantity="flux",
    value=1000.0,
    model_name="AP8MIN",
):
    return {
        "particle_type": particle_type,
        "quantity": quantity,
        "value": value,
        "model_name": model_name,
    }


class TestValidateExperimentalRecord(unittest.TestCase):

    def test_valid_record_passes(self):
        rec = _make_exp()
        valid, issues = validate_experimental_record(rec)
        self.assertTrue(valid)
        self.assertEqual(issues, [])

    def test_missing_required_field_fails(self):
        rec = _make_exp()
        del rec["provenance"]
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("provenance" in i for i in issues))

    def test_negative_value_fails(self):
        rec = _make_exp(value=-1.0)
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("value" in i for i in issues))

    def test_uncertainty_pct_above_100_fails(self):
        rec = _make_exp(uncertainty_pct=101.0)
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("uncertainty_pct" in i for i in issues))

    def test_invalid_particle_type_fails(self):
        rec = _make_exp(particle_type="neutron")
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("particle_type" in i for i in issues))

    def test_invalid_quality_flag_fails(self):
        rec = _make_exp(quality_flag="good")
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("quality_flag" in i for i in issues))

    def test_zero_duration_fails(self):
        rec = _make_exp(duration_s=0)
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("duration_s" in i for i in issues))

    def test_empty_source_fails(self):
        rec = _make_exp(source="   ")
        valid, issues = validate_experimental_record(rec)
        self.assertFalse(valid)
        self.assertTrue(any("source" in i for i in issues))


class TestComputeOffsetPct(unittest.TestCase):

    def test_equal_values_give_zero_offset(self):
        exp = _make_exp(value=500.0)
        ref = _make_ref(value=500.0)
        self.assertAlmostEqual(compute_offset_pct(exp, ref), 0.0)

    def test_experimental_above_reference_is_positive(self):
        exp = _make_exp(value=1200.0)
        ref = _make_ref(value=1000.0)
        self.assertAlmostEqual(compute_offset_pct(exp, ref), 20.0)

    def test_experimental_below_reference_is_negative(self):
        exp = _make_exp(value=800.0)
        ref = _make_ref(value=1000.0)
        self.assertAlmostEqual(compute_offset_pct(exp, ref), -20.0)

    def test_mismatched_particle_type_raises(self):
        exp = _make_exp(particle_type="proton")
        ref = _make_ref(particle_type="electron")
        with self.assertRaises(AssessmentError):
            compute_offset_pct(exp, ref)

    def test_mismatched_quantity_raises(self):
        exp = _make_exp(quantity="flux")
        ref = _make_ref(quantity="dose")
        with self.assertRaises(AssessmentError):
            compute_offset_pct(exp, ref)


class TestAssessSupersedes(unittest.TestCase):

    def test_valid_low_uncertainty_small_offset_supersedes(self):
        exp = _make_exp(quality_flag="valid", uncertainty_pct=10.0)
        supersedes, rationale = assess_supersedes_model(exp, offset_pct=15.0)
        self.assertTrue(supersedes)
        self.assertIn("Supersedure accepted", rationale)

    def test_suspect_quality_does_not_supersede(self):
        exp = _make_exp(quality_flag="suspect", uncertainty_pct=10.0)
        supersedes, rationale = assess_supersedes_model(exp, offset_pct=5.0)
        self.assertFalse(supersedes)
        self.assertIn("quality_flag", rationale)

    def test_high_uncertainty_does_not_supersede(self):
        exp = _make_exp(
            quality_flag="valid",
            uncertainty_pct=MAX_SUPERSEDE_UNCERTAINTY_PCT + 1.0,
        )
        supersedes, rationale = assess_supersedes_model(exp, offset_pct=5.0)
        self.assertFalse(supersedes)
        self.assertIn("uncertainty_pct", rationale)

    def test_large_offset_does_not_supersede(self):
        exp = _make_exp(quality_flag="valid", uncertainty_pct=10.0)
        supersedes, rationale = assess_supersedes_model(
            exp, offset_pct=MAX_OFFSET_FOR_SUPERSEDE_PCT + 1.0
        )
        self.assertFalse(supersedes)
        self.assertIn("offset", rationale.lower())

    def test_exactly_at_uncertainty_threshold_supersedes(self):
        exp = _make_exp(
            quality_flag="valid", uncertainty_pct=MAX_SUPERSEDE_UNCERTAINTY_PCT
        )
        supersedes, _ = assess_supersedes_model(exp, offset_pct=0.0)
        self.assertTrue(supersedes)


class TestComputeCombinedAssessment(unittest.TestCase):

    def test_supersedes_returns_experimental_value(self):
        exp = _make_exp(value=1200.0, uncertainty_pct=10.0)
        ref = _make_ref(value=1000.0)
        val, unc = compute_combined_assessment(exp, ref, supersedes=True)
        self.assertAlmostEqual(val, 1200.0)
        self.assertAlmostEqual(unc, 10.0)

    def test_weighted_average_pulls_toward_precise_measurement(self):
        # Low-uncertainty experimental (5%) vs higher-uncertainty model (30%)
        exp = _make_exp(value=1200.0, uncertainty_pct=5.0)
        ref = _make_ref(value=1000.0)
        val, unc = compute_combined_assessment(
            exp, ref, supersedes=False, model_uncertainty_pct=30.0
        )
        # Combined value closer to experimental (more precise)
        self.assertGreater(val, 1100.0)
        self.assertLess(val, 1200.0)
        # Combined uncertainty less than either input
        self.assertLess(unc, 5.0)

    def test_equal_absolute_uncertainty_gives_midpoint(self):
        # For equal inverse-variance weights the combined value is the arithmetic midpoint.
        # Equal absolute uncertainties require: unc_exp/100 * val_exp == model_unc/100 * val_ref
        # → model_unc = (0.20 * 800) / 1200 * 100 = 13.333...%
        exp = _make_exp(value=800.0, uncertainty_pct=20.0)
        ref = _make_ref(value=1200.0)
        model_unc = 100.0 * (0.20 * 800.0) / 1200.0  # ensures sigma_exp == sigma_ref
        val, unc = compute_combined_assessment(
            exp, ref, supersedes=False, model_uncertainty_pct=model_unc
        )
        self.assertAlmostEqual(val, 1000.0, places=5)

    def test_nonpositive_reference_raises(self):
        exp = _make_exp(value=500.0)
        ref = _make_ref(value=0.0)
        with self.assertRaises(AssessmentError):
            compute_combined_assessment(exp, ref, supersedes=False)


class TestCheckProvenance(unittest.TestCase):

    def test_complete_provenance_passes(self):
        rec = _make_exp()
        complete, missing = check_provenance(rec)
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_missing_source_flagged(self):
        rec = {"particle_type": "proton", "quantity": "flux",
               "value": 100.0, "uncertainty_pct": 10.0,
               "duration_s": 3600.0, "quality_flag": "valid",
               "source": "", "provenance": "some-doc"}
        complete, missing = check_provenance(rec)
        self.assertFalse(complete)
        self.assertIn("source", missing)

    def test_missing_provenance_text_flagged(self):
        rec = _make_exp()
        rec = dict(rec)
        rec["provenance"] = "   "
        complete, missing = check_provenance(rec)
        self.assertFalse(complete)
        self.assertIn("provenance", missing)

    def test_zero_duration_flagged(self):
        rec = _make_exp()
        rec = dict(rec)
        rec["duration_s"] = 0
        complete, missing = check_provenance(rec)
        self.assertFalse(complete)
        self.assertIn("duration_s", missing)


class TestRunBackgroundAssessment(unittest.TestCase):

    def _base_exp(self):
        return _make_exp(value=1050.0, uncertainty_pct=8.0, quality_flag="valid")

    def _base_ref(self):
        return _make_ref(value=1000.0, model_name="AP8MIN")

    def test_happy_path_returns_result(self):
        results = run_background_assessment(
            [self._base_exp()],
            [self._base_ref()],
        )
        key = ("proton", "flux")
        self.assertIn(key, results)
        r = results[key]
        self.assertAlmostEqual(r["offset_pct"], 5.0)
        self.assertTrue(r["supersedes"])
        self.assertAlmostEqual(r["combined_value"], 1050.0)
        self.assertEqual(r["issues"], [])

    def test_no_matching_reference_flagged(self):
        exp = _make_exp(particle_type="gamma", quantity="dose_rate", value=0.05)
        results = run_background_assessment([exp], [self._base_ref()])
        key = ("gamma", "dose_rate")
        self.assertIn(key, results)
        r = results[key]
        self.assertIsNone(r["reference_value"])
        self.assertTrue(any("No reference" in i for i in r["issues"]))

    def test_invalid_experimental_raises(self):
        exp = _make_exp(value=-1.0)
        with self.assertRaises(AssessmentError):
            run_background_assessment([exp], [self._base_ref()])

    def test_invalid_reference_raises(self):
        ref = _make_ref(value=0.0)
        with self.assertRaises(AssessmentError):
            run_background_assessment([self._base_exp()], [ref])

    def test_suspect_quality_does_not_supersede_in_full_run(self):
        exp = _make_exp(value=1050.0, uncertainty_pct=8.0, quality_flag="suspect")
        results = run_background_assessment([exp], [self._base_ref()])
        r = results[("proton", "flux")]
        self.assertFalse(r["supersedes"])

    def test_non_superseding_combined_value_between_exp_and_ref(self):
        # High uncertainty → does not supersede; combined must lie between 800 and 1000
        exp = _make_exp(value=800.0, uncertainty_pct=25.0, quality_flag="valid")
        results = run_background_assessment(
            [exp], [self._base_ref()], model_uncertainty_pct=DEFAULT_MODEL_UNCERTAINTY_PCT
        )
        r = results[("proton", "flux")]
        self.assertFalse(r["supersedes"])
        self.assertGreater(r["combined_value"], 800.0)
        self.assertLess(r["combined_value"], 1000.0)

    def test_provenance_complete_flag_set_on_valid_record(self):
        results = run_background_assessment(
            [self._base_exp()], [self._base_ref()]
        )
        r = results[("proton", "flux")]
        self.assertTrue(r["provenance_complete"])
        self.assertEqual(r["provenance_missing"], [])

    def test_multiple_particle_types_assessed_independently(self):
        exp_p = _make_exp(particle_type="proton", quantity="flux",
                          value=1050.0, uncertainty_pct=8.0)
        exp_e = _make_exp(particle_type="electron", quantity="flux",
                          value=5000.0, uncertainty_pct=12.0)
        ref_p = _make_ref(particle_type="proton", quantity="flux",
                          value=1000.0, model_name="AP8MIN")
        ref_e = _make_ref(particle_type="electron", quantity="flux",
                          value=4800.0, model_name="AE8MIN")
        results = run_background_assessment([exp_p, exp_e], [ref_p, ref_e])
        self.assertIn(("proton", "flux"), results)
        self.assertIn(("electron", "flux"), results)
        self.assertAlmostEqual(results[("proton", "flux")]["offset_pct"], 5.0)
        expected_e_offset = (5000.0 - 4800.0) / 4800.0 * 100.0
        self.assertAlmostEqual(
            results[("electron", "flux")]["offset_pct"], expected_e_offset, places=5
        )


if __name__ == "__main__":
    unittest.main()
