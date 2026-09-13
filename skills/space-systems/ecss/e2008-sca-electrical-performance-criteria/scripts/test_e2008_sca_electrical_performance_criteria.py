"""Contract tests for the clause 6.4.3.3.3 electrical performance criteria."""

import unittest

from e2008_sca_electrical_performance_criteria_logic import (
    ABOVE_MINIMUM,
    BELOW_MINIMUM,
    BELOW_MINIMUM_CURRENT,
    CONTROL_DRAWING,
    DEFAULT_CRITERIA_POLICY,
    DRAWING_LIMITS_NOT_CREDIBLE,
    IRRADIATION_NOT_DEMONSTRATED,
    LIMIT_SOURCE_NOT_ACCEPTED,
    PERFORMANCE_CRITERIA_MET,
    UNRESOLVED_AGAINST_MINIMUM,
    WITHIN_MEASUREMENT_UNCERTAINTY,
    assess_electrical_performance_criteria,
    current_outcome,
    degradation_fraction,
    drawing_retention_is_sensible,
    fluence_demonstrates_criterion,
    guard_band_a,
    limit_source_accepted,
    margin_fraction,
    retention_fraction,
    validate_control_drawing_limits,
    validate_criteria_policy,
)

QUALIFICATION_FLUENCE = 1.0e15


def _policy(**overrides):
    policy = dict(DEFAULT_CRITERIA_POLICY)
    policy.update(overrides)
    return policy


def _limits(**overrides):
    limits = {
        "source": CONTROL_DRAWING,
        "drawing_reference": "sca-control-drawing-rev-c",
        "min_current_before_a": 0.500,
        "min_current_after_a": 0.425,
        "qualification_fluence_e_per_cm2": QUALIFICATION_FLUENCE,
    }
    limits.update(overrides)
    return limits


def _case(**overrides):
    case = {
        "limits": _limits(),
        "delivered_fluence_e_per_cm2": QUALIFICATION_FLUENCE,
        "measured_current_before_a": 0.520,
        "measured_current_after_a": 0.448,
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_criteria_policy(DEFAULT_CRITERIA_POLICY), DEFAULT_CRITERIA_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy("control drawing")

    def test_empty_accepted_source_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(_policy(accepted_limit_sources=()))

    def test_negative_measurement_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(_policy(measurement_uncertainty_fraction=-0.01))

    def test_inverted_retention_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(
                _policy(min_retention_fraction=0.9, max_retention_fraction=0.5)
            )


class LimitSourceTests(unittest.TestCase):
    def test_the_control_drawing_is_an_accepted_source(self):
        self.assertTrue(limit_source_accepted(CONTROL_DRAWING))

    def test_a_supplier_datasheet_is_not_an_accepted_source(self):
        self.assertFalse(limit_source_accepted("supplier-datasheet-typical"))

    def test_an_empty_source_name_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_source_accepted("   ")

    def test_a_non_string_source_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_source_accepted(17)


class LimitValidationTests(unittest.TestCase):
    def test_a_well_formed_limit_pair_validates(self):
        validated = validate_control_drawing_limits(_limits())
        self.assertEqual(validated["drawing_reference"], "sca-control-drawing-rev-c")
        self.assertEqual(validated["source"], CONTROL_DRAWING)

    def test_a_missing_drawing_reference_is_rejected(self):
        limits = _limits()
        del limits["drawing_reference"]
        with self.assertRaises(ValueError):
            validate_control_drawing_limits(limits)

    def test_an_after_minimum_above_the_before_minimum_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing_limits(_limits(min_current_after_a=0.6))

    def test_equal_minima_are_accepted_as_a_no_degradation_criterion(self):
        limits = validate_control_drawing_limits(_limits(min_current_after_a=0.500))
        self.assertAlmostEqual(
            limits["min_current_after_a"], limits["min_current_before_a"], places=12
        )

    def test_a_zero_minimum_current_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing_limits(_limits(min_current_before_a=0.0))

    def test_a_missing_qualification_fluence_is_rejected(self):
        limits = _limits()
        del limits["qualification_fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            validate_control_drawing_limits(limits)

    def test_a_non_mapping_limit_block_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_drawing_limits(["0.5", "0.425"])


class FractionTests(unittest.TestCase):
    def test_retention_is_the_after_over_before_ratio(self):
        self.assertAlmostEqual(
            _ratio(retention_fraction(0.425, 0.500), 0.85), 1.0, places=12
        )

    def test_degradation_completes_the_retention(self):
        self.assertAlmostEqual(
            retention_fraction(0.425, 0.500) + degradation_fraction(0.425, 0.500),
            1.0,
            places=12,
        )

    def test_a_zero_before_current_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_fraction(0.425, 0.0)

    def test_margin_is_zero_at_the_minimum(self):
        self.assertAlmostEqual(margin_fraction(0.500, 0.500), 0.0, places=12)

    def test_margin_is_negative_below_the_minimum(self):
        self.assertLess(margin_fraction(0.400, 0.500), 0.0)

    def test_the_guard_band_scales_with_the_minimum(self):
        self.assertAlmostEqual(
            _ratio(guard_band_a(0.500), 0.005), 1.0, places=12
        )

    def test_a_negative_measured_current_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_fraction(-0.1, 0.5)


class OutcomeTests(unittest.TestCase):
    def test_a_comfortable_current_is_above_the_minimum(self):
        self.assertEqual(current_outcome(0.520, 0.500), ABOVE_MINIMUM)

    def test_a_current_exactly_at_the_guard_band_edge_is_above_the_minimum(self):
        band = guard_band_a(0.500)
        self.assertAlmostEqual(band, 0.005, places=9)
        self.assertEqual(current_outcome(0.500 + band, 0.500), ABOVE_MINIMUM)

    def test_a_current_at_the_bare_minimum_is_unresolved(self):
        self.assertEqual(current_outcome(0.500, 0.500), UNRESOLVED_AGAINST_MINIMUM)

    def test_a_current_just_inside_the_band_is_unresolved(self):
        self.assertEqual(current_outcome(0.4975, 0.500), UNRESOLVED_AGAINST_MINIMUM)

    def test_a_current_well_under_the_band_is_below_the_minimum(self):
        self.assertEqual(current_outcome(0.400, 0.500), BELOW_MINIMUM)

    def test_a_zero_uncertainty_policy_resolves_the_bare_minimum(self):
        policy = _policy(measurement_uncertainty_fraction=0.0)
        self.assertEqual(current_outcome(0.500, 0.500, policy), ABOVE_MINIMUM)


class DrawingCredibilityTests(unittest.TestCase):
    def test_a_fifteen_per_cent_degradation_criterion_is_credible(self):
        self.assertTrue(drawing_retention_is_sensible(_limits()))

    def test_a_criterion_at_the_retention_floor_is_credible(self):
        limits = _limits(min_current_after_a=0.350)
        self.assertAlmostEqual(
            retention_fraction(0.350, 0.500),
            DEFAULT_CRITERIA_POLICY["min_retention_fraction"],
            places=9,
        )
        self.assertTrue(drawing_retention_is_sensible(limits))

    def test_a_criterion_demanding_almost_no_loss_of_current_is_not_credible(self):
        self.assertFalse(
            drawing_retention_is_sensible(_limits(min_current_after_a=0.100))
        )

    def test_the_exposure_at_the_qualification_fluence_demonstrates_it(self):
        self.assertTrue(
            fluence_demonstrates_criterion(QUALIFICATION_FLUENCE, _limits())
        )

    def test_a_lighter_exposure_does_not_demonstrate_it(self):
        self.assertFalse(
            fluence_demonstrates_criterion(1.0e13, _limits())
        )

    def test_a_zero_delivered_fluence_is_rejected(self):
        with self.assertRaises(ValueError):
            fluence_demonstrates_criterion(0.0, _limits())


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_pair_of_currents_meets_the_criteria(self):
        result = assess_electrical_performance_criteria(_case())
        self.assertEqual(result["verdict"], PERFORMANCE_CRITERIA_MET)
        self.assertEqual(result["findings"], [])

    def test_the_margins_are_reported_for_both_measurements(self):
        result = assess_electrical_performance_criteria(_case())
        self.assertGreater(result["margin_before_fraction"], 0.0)
        self.assertGreater(result["margin_after_fraction"], 0.0)

    def test_the_measured_retention_is_reported(self):
        result = assess_electrical_performance_criteria(_case())
        self.assertAlmostEqual(
            _ratio(result["measured_retention_fraction"], 0.448 / 0.520),
            1.0,
            places=12,
        )

    def test_a_datasheet_limit_source_blocks_the_judgement(self):
        result = assess_electrical_performance_criteria(
            _case(limits=_limits(source="supplier-datasheet-typical"))
        )
        self.assertEqual(result["verdict"], LIMIT_SOURCE_NOT_ACCEPTED)
        self.assertTrue(result["findings"])

    def test_an_incredible_drawing_pair_blocks_the_judgement(self):
        result = assess_electrical_performance_criteria(
            _case(limits=_limits(min_current_after_a=0.100))
        )
        self.assertEqual(result["verdict"], DRAWING_LIMITS_NOT_CREDIBLE)

    def test_an_under_delivered_fluence_does_not_demonstrate_the_criterion(self):
        result = assess_electrical_performance_criteria(
            _case(delivered_fluence_e_per_cm2=1.0e13)
        )
        self.assertEqual(result["verdict"], IRRADIATION_NOT_DEMONSTRATED)
        self.assertFalse(result["fluence_demonstrates_criterion"])

    def test_a_low_pre_irradiation_current_fails(self):
        result = assess_electrical_performance_criteria(
            _case(measured_current_before_a=0.400)
        )
        self.assertEqual(result["verdict"], BELOW_MINIMUM_CURRENT)
        self.assertEqual(result["before_outcome"], BELOW_MINIMUM)

    def test_a_low_post_irradiation_current_fails(self):
        result = assess_electrical_performance_criteria(
            _case(measured_current_after_a=0.300)
        )
        self.assertEqual(result["verdict"], BELOW_MINIMUM_CURRENT)
        self.assertEqual(result["after_outcome"], BELOW_MINIMUM)

    def test_both_failures_are_reported_not_only_the_first(self):
        result = assess_electrical_performance_criteria(
            _case(measured_current_before_a=0.400, measured_current_after_a=0.300)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_a_current_inside_the_uncertainty_band_resolves_neither_way(self):
        result = assess_electrical_performance_criteria(
            _case(measured_current_after_a=0.425)
        )
        self.assertEqual(result["verdict"], WITHIN_MEASUREMENT_UNCERTAINTY)
        self.assertEqual(result["after_outcome"], UNRESOLVED_AGAINST_MINIMUM)

    def test_a_fail_outranks_an_unresolved_measurement(self):
        result = assess_electrical_performance_criteria(
            _case(measured_current_before_a=0.500, measured_current_after_a=0.300)
        )
        self.assertEqual(result["verdict"], BELOW_MINIMUM_CURRENT)

    def test_the_drawing_reference_travels_with_the_result(self):
        result = assess_electrical_performance_criteria(_case())
        self.assertEqual(result["drawing_reference"], "sca-control-drawing-rev-c")

    def test_an_absent_delivered_fluence_is_rejected(self):
        case = _case()
        del case["delivered_fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            assess_electrical_performance_criteria(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_performance_criteria(["limits"])

    def test_a_missing_measured_current_is_rejected(self):
        case = _case()
        del case["measured_current_after_a"]
        with self.assertRaises(ValueError):
            assess_electrical_performance_criteria(case)


if __name__ == "__main__":
    unittest.main()
