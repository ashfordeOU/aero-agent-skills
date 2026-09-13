"""Contract tests for the clause 6.4.3.14.1 reverse-bias test purpose logic."""

import unittest

from e2008_reverse_bias_test_purpose_logic import (
    DEFAULT_RESOLUTION_MARGIN,
    DEGRADATION_FOUND,
    EVIDENCE_INCOMPLETE,
    MEASURED_KEYS,
    NOT_DEMONSTRATED,
    PERFORMANCE_PARAMETERS,
    PERFORMANCE_RETAINED,
    PURPOSE_OBJECTIVES,
    assess_parameter,
    assess_parameters,
    evaluate_purpose,
    maximum_power,
    objective_parameter,
    relative_loss,
    resolution_is_adequate,
    validate_characterisation,
)

# A three-cell assembly characterised under an illuminated sweep before and
# after a reverse-bias exposure. The post-exposure pair loses one percent of
# the maximum-power current and nothing else.
BEFORE = {"isc_a": 0.500, "voc_v": 8.10, "imp_a": 0.470, "vmp_v": 6.90}
AFTER_CLEAN = {"isc_a": 0.500, "voc_v": 8.10, "imp_a": 0.4653, "vmp_v": 6.90}
AFTER_SHUNTED = {"isc_a": 0.499, "voc_v": 7.20, "imp_a": 0.440, "vmp_v": 5.90}

ALLOWANCES = {"isc_a": 0.02, "voc_v": 0.02, "pmax_w": 0.02}
UNCERTAINTIES = {"isc_a": 0.004, "voc_v": 0.004, "pmax_w": 0.005}


def _spec(**overrides):
    spec = {
        "before": dict(BEFORE),
        "after": dict(AFTER_CLEAN),
        "objectives": ["reverse-bias-power-retention", "reverse-bias-active-area-loss"],
        "allowances": dict(ALLOWANCES),
        "uncertainties": dict(UNCERTAINTIES),
    }
    spec.update(overrides)
    return spec


class CharacterisationValidationTests(unittest.TestCase):
    def test_valid_record_derives_maximum_power(self):
        record = validate_characterisation(BEFORE)
        self.assertAlmostEqual(record["pmax_w"], 0.470 * 6.90, places=9)

    def test_every_measured_key_is_required(self):
        for key in MEASURED_KEYS:
            broken = dict(BEFORE)
            del broken[key]
            with self.assertRaises(ValueError):
                validate_characterisation(broken)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation(["isc_a"])

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation(dict(BEFORE, isc_a=0.0))

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation(dict(BEFORE, voc_v=True))

    def test_maximum_power_current_above_short_circuit_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation(dict(BEFORE, imp_a=0.600))

    def test_maximum_power_voltage_above_open_circuit_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation(dict(BEFORE, vmp_v=9.00))

    def test_maximum_power_point_on_the_corner_is_accepted(self):
        record = validate_characterisation(
            {"isc_a": 0.5, "voc_v": 8.1, "imp_a": 0.5, "vmp_v": 8.1}
        )
        self.assertAlmostEqual(record["pmax_w"], 0.5 * 8.1, places=9)


class MaximumPowerTests(unittest.TestCase):
    def test_power_is_the_product_of_the_knee_pair(self):
        self.assertAlmostEqual(maximum_power({"imp_a": 2.0, "vmp_v": 3.5}), 7.0, places=9)

    def test_missing_knee_key_rejected(self):
        with self.assertRaises(ValueError):
            maximum_power({"imp_a": 2.0})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            maximum_power(7.0)


class RelativeLossTests(unittest.TestCase):
    def test_loss_is_a_positive_fraction(self):
        self.assertAlmostEqual(relative_loss(10.0, 9.0), 0.1, places=9)

    def test_no_change_is_zero_loss(self):
        self.assertAlmostEqual(relative_loss(10.0, 10.0), 0.0, places=9)

    def test_improvement_is_a_negative_loss(self):
        self.assertAlmostEqual(relative_loss(10.0, 11.0), -0.1, places=9)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss(0.0, 1.0)

    def test_negative_after_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss(10.0, -1.0)


class ResolutionTests(unittest.TestCase):
    def test_allowance_well_clear_of_noise_is_adequate(self):
        self.assertTrue(resolution_is_adequate(0.02, 0.004))

    def test_allowance_exactly_on_the_margin_is_adequate(self):
        self.assertTrue(resolution_is_adequate(0.012, 0.004, 3.0))

    def test_allowance_inside_the_noise_is_not_adequate(self):
        self.assertFalse(resolution_is_adequate(0.005, 0.004, 3.0))

    def test_default_margin_is_three(self):
        self.assertAlmostEqual(DEFAULT_RESOLUTION_MARGIN, 3.0, places=9)

    def test_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolution_is_adequate(1.5, 0.004)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            resolution_is_adequate(0.02, -0.001)


class ObjectiveTests(unittest.TestCase):
    def test_power_retention_rests_on_maximum_power(self):
        self.assertEqual(objective_parameter("reverse-bias-power-retention"), "pmax_w")

    def test_case_and_space_are_absorbed(self):
        self.assertEqual(
            objective_parameter("  Reverse-Bias-Junction-Integrity "), "voc_v"
        )

    def test_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            objective_parameter("reverse-bias-colour-change")

    def test_every_objective_names_a_known_parameter(self):
        for parameter in PURPOSE_OBJECTIVES.values():
            self.assertIn(parameter, PERFORMANCE_PARAMETERS)


class ParameterAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.before = validate_characterisation(BEFORE)
        self.after = validate_characterisation(AFTER_CLEAN)

    def test_small_power_loss_stays_within_allowance(self):
        record = assess_parameter("pmax_w", self.before, self.after, 0.02, 0.005)
        self.assertTrue(record["within_allowance"])
        self.assertAlmostEqual(record["relative_loss"], 0.01, places=9)

    def test_loss_exactly_on_the_allowance_is_within_it(self):
        record = assess_parameter("pmax_w", self.before, self.after, 0.01, 0.002)
        self.assertAlmostEqual(record["relative_loss"], record["allowance"], places=9)
        self.assertTrue(record["within_allowance"])

    def test_large_power_loss_breaks_the_allowance(self):
        shunted = validate_characterisation(AFTER_SHUNTED)
        record = assess_parameter("pmax_w", self.before, shunted, 0.02, 0.005)
        self.assertFalse(record["within_allowance"])

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameter("fill_factor", self.before, self.after, 0.02)

    def test_parameter_absent_from_a_side_rejected(self):
        stripped = dict(self.after)
        del stripped["pmax_w"]
        with self.assertRaises(ValueError):
            assess_parameter("pmax_w", self.before, stripped, 0.02)

    def test_records_come_back_in_parameter_order(self):
        records = assess_parameters(self.before, self.after, ALLOWANCES, UNCERTAINTIES)
        self.assertEqual(
            [r["parameter"] for r in records], ["isc_a", "voc_v", "pmax_w"]
        )

    def test_allowances_naming_nothing_recognized_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameters(self.before, self.after, {"fill_factor": 0.02})

    def test_uncertainty_for_an_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameters(
                self.before, self.after, ALLOWANCES, {"fill_factor": 0.01}
            )

    def test_empty_allowances_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameters(self.before, self.after, {})


class PurposeEvaluationTests(unittest.TestCase):
    def test_retained_performance_passes_with_no_findings(self):
        result = evaluate_purpose(_spec())
        self.assertEqual(result["outcome"], PERFORMANCE_RETAINED)
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_shunted_assembly_is_reported_as_degraded(self):
        result = evaluate_purpose(_spec(after=dict(AFTER_SHUNTED)))
        self.assertEqual(result["outcome"], DEGRADATION_FOUND)
        self.assertFalse(result["passed"])

    def test_missing_post_exposure_record_demonstrates_nothing(self):
        result = evaluate_purpose(_spec(after=None))
        self.assertEqual(result["outcome"], NOT_DEMONSTRATED)
        self.assertEqual(len(result["findings"]), 2)
        self.assertEqual(result["parameters"], [])

    def test_objective_without_an_allowance_leaves_evidence_incomplete(self):
        result = evaluate_purpose(
            _spec(
                objectives=["reverse-bias-shunt-path-formation"],
                allowances={"isc_a": 0.02},
                uncertainties={"isc_a": 0.004},
            )
        )
        self.assertEqual(result["outcome"], EVIDENCE_INCOMPLETE)
        self.assertIn("maximum-power voltage", result["findings"][0])

    def test_allowance_inside_the_noise_leaves_evidence_incomplete(self):
        result = evaluate_purpose(
            _spec(allowances={"pmax_w": 0.014}, uncertainties={"pmax_w": 0.006},
                  objectives=["reverse-bias-power-retention"])
        )
        self.assertEqual(result["outcome"], EVIDENCE_INCOMPLETE)

    def test_degradation_outranks_an_unresolvable_allowance(self):
        result = evaluate_purpose(
            _spec(
                after=dict(AFTER_SHUNTED),
                allowances={"pmax_w": 0.006},
                uncertainties={"pmax_w": 0.005},
                objectives=["reverse-bias-power-retention"],
            )
        )
        self.assertEqual(result["outcome"], DEGRADATION_FOUND)

    def test_repeated_objective_is_collapsed(self):
        result = evaluate_purpose(
            _spec(objectives=["reverse-bias-power-retention",
                              "Reverse-Bias-Power-Retention"])
        )
        self.assertEqual(len(result["objectives"]), 1)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["allowances"]
        with self.assertRaises(ValueError):
            evaluate_purpose(spec)

    def test_empty_objectives_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_purpose(_spec(objectives=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_purpose(["before"])

    def test_unknown_objective_in_the_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_purpose(_spec(objectives=["reverse-bias-mass-growth"]))


if __name__ == "__main__":
    unittest.main()
