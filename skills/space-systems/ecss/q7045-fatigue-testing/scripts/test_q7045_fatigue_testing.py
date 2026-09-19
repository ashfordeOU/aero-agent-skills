"""Contract tests for the S-N fatigue reduction logic.

The reference set sits exactly on log10(N) = 17 - 5 log10(S), so the fit has
a known answer. The cases read the set the way a reviewer does: which points
were allowed into the fit, what the run-outs are entitled to claim, and
whether the frequency and the specimen form make the curve transferable.
"""

import unittest

from q7045_fatigue_testing_logic import (
    FREQUENCY_BAND_HZ,
    SPECIMEN_TYPES,
    assess_fatigue_test,
    fit_basquin,
    frequency_findings,
    life_at_stress,
    runout_findings,
    specimen_findings,
    stress_at_life,
    validate_sn_points,
)

INTERCEPT = 17.0
EXPONENT = -5.0
RUNOUT_CYCLES = 5.0e7


def _life(stress):
    """Return the reference life 1e17 / S^5 without calling a power routine."""
    return 1.0e17 / (stress * stress * stress * stress * stress)


def _failure(stress):
    return {"stress_amplitude_mpa": stress, "cycles": _life(stress), "runout": False}


def _points(**overrides):
    points = [_failure(100.0), _failure(200.0), _failure(400.0),
              {"stress_amplitude_mpa": 60.0, "cycles": 2.0e8, "runout": True}]
    if "replace" in overrides:
        index, point = overrides["replace"]
        points[index] = point
    return points


def _spec(**overrides):
    spec = {
        "points": _points(),
        "specimen_type": "unnotched-axial",
        "frequency_hz": 20.0,
        "runout_cycles": RUNOUT_CYCLES,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_reference_set_validates(self):
        self.assertEqual(len(validate_sn_points(_points())), 4)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_sn_points([])

    def test_missing_cycles_rejected(self):
        with self.assertRaises(ValueError):
            validate_sn_points([{"stress_amplitude_mpa": 100.0}])

    def test_zero_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_sn_points([{"stress_amplitude_mpa": 0.0, "cycles": 1.0e6}])

    def test_non_boolean_runout_rejected(self):
        with self.assertRaises(ValueError):
            validate_sn_points(
                [{"stress_amplitude_mpa": 100.0, "cycles": 1.0e6, "runout": "yes"}]
            )

    def test_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_sn_points([{"stress_amplitude_mpa": 100.0, "cycles": 0.5}])


class FitTests(unittest.TestCase):
    def test_fit_recovers_the_reference_exponent(self):
        fit = fit_basquin(_points())
        self.assertAlmostEqual(fit["exponent"], EXPONENT, places=6)

    def test_fit_recovers_the_reference_intercept(self):
        fit = fit_basquin(_points())
        self.assertAlmostEqual(fit["intercept"], INTERCEPT, places=5)

    def test_fit_quality_is_unity_on_exact_data(self):
        fit = fit_basquin(_points())
        self.assertAlmostEqual(fit["fit_quality"], 1.0, places=9)

    def test_runouts_are_censored_from_the_fit(self):
        fit = fit_basquin(_points())
        self.assertEqual(fit["failures_used"], 3)
        self.assertEqual(fit["runouts_censored"], 1)

    def test_two_failures_are_not_enough_to_fit(self):
        with self.assertRaises(ValueError):
            fit_basquin([_failure(100.0), _failure(200.0)])

    def test_a_single_stress_level_cannot_be_fitted(self):
        with self.assertRaises(ValueError):
            fit_basquin([
                {"stress_amplitude_mpa": 100.0, "cycles": 1.0e6},
                {"stress_amplitude_mpa": 100.0, "cycles": 2.0e6},
                {"stress_amplitude_mpa": 100.0, "cycles": 3.0e6},
            ])

    def test_a_curve_rising_with_stress_is_rejected(self):
        with self.assertRaises(ValueError):
            fit_basquin([
                {"stress_amplitude_mpa": 100.0, "cycles": 1.0e4},
                {"stress_amplitude_mpa": 200.0, "cycles": 1.0e5},
                {"stress_amplitude_mpa": 400.0, "cycles": 1.0e6},
            ])


class PredictionTests(unittest.TestCase):
    def test_life_at_the_reference_stress(self):
        fit = fit_basquin(_points())
        self.assertAlmostEqual(life_at_stress(fit, 100.0) / 1.0e7, 1.0, places=6)

    def test_doubling_the_stress_cuts_life_by_thirty_two(self):
        fit = fit_basquin(_points())
        near = life_at_stress(fit, 100.0)
        far = life_at_stress(fit, 200.0)
        self.assertAlmostEqual(near / (32.0 * far), 1.0, places=6)

    def test_stress_at_life_inverts_life_at_stress(self):
        fit = fit_basquin(_points())
        life = life_at_stress(fit, 150.0)
        self.assertAlmostEqual(stress_at_life(fit, life) / 150.0, 1.0, places=6)

    def test_life_at_zero_stress_rejected(self):
        fit = fit_basquin(_points())
        with self.assertRaises(ValueError):
            life_at_stress(fit, 0.0)

    def test_malformed_fit_rejected(self):
        with self.assertRaises(ValueError):
            life_at_stress({"slope": -5.0}, 100.0)

    def test_stress_at_zero_life_rejected(self):
        fit = fit_basquin(_points())
        with self.assertRaises(ValueError):
            stress_at_life(fit, 0.0)


class RunoutTests(unittest.TestCase):
    def test_consistent_runout_is_silent(self):
        fit = fit_basquin(_points())
        self.assertEqual(runout_findings(_points(), fit, RUNOUT_CYCLES), [])

    def test_runout_below_the_declared_threshold_is_reported(self):
        points = _points(replace=(3, {"stress_amplitude_mpa": 60.0,
                                      "cycles": 1.0e6, "runout": True}))
        fit = fit_basquin(points)
        notes = runout_findings(points, fit, RUNOUT_CYCLES)
        self.assertEqual(len(notes), 1)
        self.assertIn("below the", notes[0])

    def test_uninformative_runout_is_reported(self):
        points = _points(replace=(3, {"stress_amplitude_mpa": 60.0,
                                      "cycles": 6.0e7, "runout": True}))
        fit = fit_basquin(points)
        notes = runout_findings(points, fit, RUNOUT_CYCLES)
        self.assertEqual(len(notes), 1)
        self.assertIn("constrains nothing", notes[0])

    def test_failure_beyond_the_threshold_is_reported(self):
        points = _points(replace=(3, {"stress_amplitude_mpa": 60.0,
                                      "cycles": 2.0e8, "runout": False}))
        fit = fit_basquin(points)
        notes = runout_findings(points, fit, RUNOUT_CYCLES)
        self.assertEqual(len(notes), 1)
        self.assertIn("beyond the declared", notes[0])

    def test_zero_threshold_rejected(self):
        fit = fit_basquin(_points())
        with self.assertRaises(ValueError):
            runout_findings(_points(), fit, 0.0)


class ConditionTests(unittest.TestCase):
    def test_frequency_inside_the_band_is_silent(self):
        self.assertEqual(frequency_findings(20.0), [])

    def test_frequency_exactly_at_the_lower_bound_is_silent(self):
        self.assertEqual(frequency_findings(FREQUENCY_BAND_HZ[0]), [])

    def test_fast_cycling_is_reported(self):
        notes = frequency_findings(500.0)
        self.assertEqual(len(notes), 1)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            frequency_findings(20.0, (100.0, 1.0))

    def test_four_specimen_forms_are_recognised(self):
        self.assertEqual(len(SPECIMEN_TYPES), 4)

    def test_unnotched_form_is_silent(self):
        self.assertEqual(specimen_findings("unnotched-axial"), [])

    def test_notched_form_without_a_factor_is_reported(self):
        notes = specimen_findings("notched-axial")
        self.assertEqual(len(notes), 1)
        self.assertIn("stress concentration", notes[0])

    def test_notched_form_with_a_factor_is_silent(self):
        self.assertEqual(specimen_findings("notched-axial", 3.0), [])

    def test_factor_below_unity_is_reported(self):
        notes = specimen_findings("notched-axial", 0.5)
        self.assertEqual(len(notes), 1)
        self.assertIn("below unity", notes[0])

    def test_factor_on_an_unnotched_form_is_reported(self):
        notes = specimen_findings("rotating-bending", 2.0)
        self.assertEqual(len(notes), 1)

    def test_unknown_specimen_form_rejected(self):
        with self.assertRaises(ValueError):
            specimen_findings("cruciform")


class AssessmentTests(unittest.TestCase):
    def test_clean_set_is_usable(self):
        result = assess_fatigue_test(_spec())
        self.assertTrue(result["curve_usable"])
        self.assertEqual(result["findings"], [])

    def test_reported_fit_matches_the_reference(self):
        result = assess_fatigue_test(_spec())
        self.assertAlmostEqual(result["exponent"], EXPONENT, places=6)
        self.assertAlmostEqual(result["intercept"], INTERCEPT, places=5)

    def test_predicted_life_at_a_design_stress(self):
        result = assess_fatigue_test(_spec(design_stress_mpa=100.0))
        self.assertAlmostEqual(
            result["predicted_life_cycles"] / 1.0e7, 1.0, places=6
        )

    def test_no_design_stress_predicts_nothing(self):
        result = assess_fatigue_test(_spec())
        self.assertIsNone(result["predicted_life_cycles"])

    def test_stress_at_the_runout_life_is_reported(self):
        result = assess_fatigue_test(_spec())
        self.assertAlmostEqual(
            life_at_stress(result, result["stress_at_runout_life"]) / RUNOUT_CYCLES,
            1.0,
            places=6,
        )

    def test_notched_set_without_a_factor_is_unusable(self):
        result = assess_fatigue_test(_spec(specimen_type="notched-axial"))
        self.assertFalse(result["curve_usable"])

    def test_notched_set_with_a_factor_is_usable(self):
        result = assess_fatigue_test(
            _spec(specimen_type="notched-axial", stress_concentration_kt=3.0)
        )
        self.assertTrue(result["curve_usable"])

    def test_fast_cycling_makes_the_curve_unusable(self):
        result = assess_fatigue_test(_spec(frequency_hz=500.0))
        self.assertFalse(result["curve_usable"])

    def test_uninformative_runout_makes_the_curve_unusable(self):
        result = assess_fatigue_test(
            _spec(points=_points(replace=(3, {"stress_amplitude_mpa": 60.0,
                                              "cycles": 6.0e7, "runout": True})))
        )
        self.assertFalse(result["curve_usable"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["runout_cycles"]
        with self.assertRaises(ValueError):
            assess_fatigue_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_fatigue_test(["points"])


if __name__ == "__main__":
    unittest.main()
