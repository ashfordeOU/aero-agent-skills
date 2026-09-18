"""Contract tests for the clause 7.1 MMIC design-principle review."""

import math
import unittest

from q6012_mmic_design_principles_logic import (
    DERATING_LIMIT_EXCEEDED,
    DESIGN_PRINCIPLES_SATISFIED,
    DESIGN_RULE_VIOLATIONS_OPEN,
    MARGIN_TOLERANCE,
    ON_WAFER_TEST_PROVISION_MISSING,
    PARAMETRIC_MARGIN_SHORTFALL,
    PREDICTED_YIELD_SHORTFALL,
    UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE,
    assess_design_principles,
    assess_parameter,
    assess_stress,
    combined_yield,
    derated_limit,
    derating_ratio,
    normal_cdf,
    parametric_margin_sigma,
    parametric_yield,
    proven_cell_fraction,
    validate_design_policy,
    validate_parameter,
    validate_stress,
)

GAIN = {"id": "small-signal-gain-db", "nominal": 22.0, "limit": 19.0, "sense": "lower", "sigma": 0.8}
POWER = {"id": "output-power-dbm", "nominal": 30.0, "limit": 28.0, "sense": "lower", "sigma": 0.5}
NOISE = {"id": "noise-figure-db", "nominal": 2.0, "limit": 3.2, "sense": "upper", "sigma": 0.3}

CHANNEL = {"kind": "channel-temperature-c", "applied": 120.0, "limit": 175.0}
CURRENT = {"kind": "metal-current-density-ma-per-um", "applied": 6.0, "limit": 10.0}
POWER_DENSITY = {"kind": "rf-power-density-w-per-mm", "applied": 3.0, "limit": 5.0}


def with_changes(base, **overrides):
    record = dict(base)
    record.update(overrides)
    return record


class PolicyTests(unittest.TestCase):
    def test_defaults_ask_for_three_sigma(self):
        self.assertAlmostEqual(validate_design_policy()["required_margin_sigma"], 3.0, places=9)

    def test_override_is_merged_over_the_defaults(self):
        rules = validate_design_policy({"required_margin_sigma": 4.0})
        self.assertAlmostEqual(rules["required_margin_sigma"], 4.0, places=9)
        self.assertAlmostEqual(rules["min_predicted_yield"], 0.95, places=9)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_policy({"required_corner_count": 5})

    def test_negative_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_policy({"required_margin_sigma": -1.0})

    def test_yield_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_policy({"min_predicted_yield": 1.4})

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_policy({"require_on_wafer_test_structures": "yes"})


class NormalTests(unittest.TestCase):
    def test_zero_margin_is_half_the_population(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5, places=12)

    def test_one_sigma_is_the_textbook_value(self):
        self.assertAlmostEqual(normal_cdf(1.0), 0.8413447461, places=9)

    def test_three_sigma_is_the_textbook_value(self):
        self.assertAlmostEqual(normal_cdf(3.0), 0.9986501020, places=9)

    def test_symmetric_about_zero(self):
        self.assertAlmostEqual(normal_cdf(-2.0) + normal_cdf(2.0), 1.0, places=12)

    def test_non_finite_argument_rejected(self):
        with self.assertRaises(ValueError):
            normal_cdf(float("nan"))

    def test_non_numeric_argument_rejected(self):
        with self.assertRaises(ValueError):
            normal_cdf("3")


class ParameterValidationTests(unittest.TestCase):
    def test_parameter_is_normalized(self):
        record = validate_parameter(GAIN)
        self.assertEqual(record["id"], "small-signal-gain-db")
        self.assertAlmostEqual(record["sigma"], 0.8, places=9)

    def test_unknown_limit_sense_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(with_changes(GAIN, sense="two-sided"))

    def test_zero_sigma_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(with_changes(GAIN, sigma=0.0))

    def test_negative_sigma_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(with_changes(GAIN, sigma=-0.5))

    def test_missing_limit_rejected(self):
        record = dict(GAIN)
        del record["limit"]
        with self.assertRaises(ValueError):
            validate_parameter(record)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(with_changes(GAIN, id="   "))

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(["small-signal-gain-db", 22.0])


class MarginTests(unittest.TestCase):
    def test_lower_limit_margin(self):
        self.assertAlmostEqual(parametric_margin_sigma(GAIN), 3.75, places=9)

    def test_upper_limit_margin(self):
        self.assertAlmostEqual(parametric_margin_sigma(NOISE), 4.0, places=9)

    def test_margin_is_negative_when_the_nominal_is_outside_the_limit(self):
        record = with_changes(GAIN, nominal=18.0)
        self.assertAlmostEqual(parametric_margin_sigma(record), -1.25, places=9)

    def test_tighter_spread_buys_margin(self):
        wide = parametric_margin_sigma(with_changes(GAIN, sigma=1.5))
        narrow = parametric_margin_sigma(with_changes(GAIN, sigma=0.5))
        self.assertAlmostEqual(narrow / wide, 3.0, places=9)

    def test_margin_exactly_at_the_requirement_is_accepted(self):
        record = assess_parameter(with_changes(GAIN, nominal=22.0, limit=19.0, sigma=1.0))
        self.assertAlmostEqual(record["margin_sigma"], 3.0, places=9)
        self.assertTrue(record["acceptable"])

    def test_margin_below_the_requirement_is_flagged(self):
        record = assess_parameter(with_changes(GAIN, sigma=1.5))
        self.assertIn(PARAMETRIC_MARGIN_SHORTFALL, record["statuses"])

    def test_requirement_can_be_raised_by_policy(self):
        record = assess_parameter(GAIN, {"required_margin_sigma": 4.5})
        self.assertIn(PARAMETRIC_MARGIN_SHORTFALL, record["statuses"])

    def test_yield_follows_the_margin(self):
        self.assertAlmostEqual(parametric_yield(3.0), normal_cdf(3.0), places=12)


class CombinedYieldTests(unittest.TestCase):
    def test_product_of_two_parameters(self):
        records = [{"yield_fraction": 0.9}, {"yield_fraction": 0.8}]
        self.assertAlmostEqual(combined_yield(records), 0.72, places=9)

    def test_single_parameter_passes_through(self):
        self.assertAlmostEqual(combined_yield([{"yield_fraction": 0.995}]), 0.995, places=9)

    def test_combined_yield_never_exceeds_the_worst_line(self):
        records = [{"yield_fraction": 0.99}, {"yield_fraction": 0.97}]
        self.assertLess(combined_yield(records), 0.97)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            combined_yield([])

    def test_out_of_range_yield_rejected(self):
        with self.assertRaises(ValueError):
            combined_yield([{"yield_fraction": 1.4}])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            combined_yield([{"id": "gain"}])


class StressTests(unittest.TestCase):
    def test_default_derating_factor_is_applied(self):
        self.assertAlmostEqual(derated_limit(CHANNEL), 175.0 * 0.80, places=9)

    def test_derating_ratio_is_against_the_derated_limit(self):
        self.assertAlmostEqual(derating_ratio(CURRENT), 6.0 / (10.0 * 0.75), places=9)

    def test_stress_within_the_derated_limit_is_acceptable(self):
        self.assertTrue(assess_stress(CHANNEL)["acceptable"])

    def test_stress_exactly_on_the_derated_limit_is_acceptable(self):
        stress = with_changes(CHANNEL, applied=derated_limit(CHANNEL))
        record = assess_stress(stress)
        self.assertAlmostEqual(record["derating_ratio"], 1.0, places=9)
        self.assertTrue(record["acceptable"])

    def test_stress_between_the_derated_and_absolute_limit_is_flagged(self):
        record = assess_stress(with_changes(CHANNEL, applied=160.0))
        self.assertIn(DERATING_LIMIT_EXCEEDED, record["statuses"])

    def test_an_explicit_derating_factor_overrides_the_default(self):
        record = assess_stress(with_changes(CHANNEL, applied=160.0, derating_factor=1.0))
        self.assertTrue(record["acceptable"])

    def test_unknown_stress_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(with_changes(CHANNEL, kind="solder-joint-shear"))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(with_changes(CHANNEL, limit=0.0))

    def test_negative_applied_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(with_changes(CHANNEL, applied=-5.0))

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(with_changes(CHANNEL, derating_factor=1.2))

    def test_non_finite_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(with_changes(CHANNEL, applied=float("inf")))


class CellTests(unittest.TestCase):
    def test_fraction_of_proven_cells(self):
        self.assertAlmostEqual(proven_cell_fraction(8, 10), 0.8, places=9)

    def test_all_novel_design_is_zero(self):
        self.assertAlmostEqual(proven_cell_fraction(0, 12), 0.0, places=9)

    def test_zero_total_rejected(self):
        with self.assertRaises(ValueError):
            proven_cell_fraction(0, 0)

    def test_proven_above_total_rejected(self):
        with self.assertRaises(ValueError):
            proven_cell_fraction(11, 10)

    def test_non_integer_counts_rejected(self):
        with self.assertRaises(ValueError):
            proven_cell_fraction(8.0, 10)


class DesignReviewTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "parameters": [GAIN, POWER, NOISE],
            "stresses": [CHANNEL, CURRENT, POWER_DENSITY],
            "cells": {"proven": 8, "total": 10},
            "drc_violations": 0,
            "on_wafer_test_structures": True,
            "test_vehicle_planned": False,
        }
        spec.update(overrides)
        return spec

    def test_sound_design_satisfies_the_principles(self):
        result = assess_design_principles(self._spec())
        self.assertEqual(result["verdict"], DESIGN_PRINCIPLES_SATISFIED)
        self.assertEqual(result["findings"], [])

    def test_predicted_yield_is_the_product_of_the_lines(self):
        result = assess_design_principles(self._spec())
        expected = 1.0
        for record in result["parameters"]:
            expected *= record["yield_fraction"]
        self.assertAlmostEqual(result["predicted_yield"], expected, places=12)

    def test_worst_margin_is_reported(self):
        result = assess_design_principles(self._spec())
        self.assertAlmostEqual(result["worst_margin_sigma"], 3.75, places=9)

    def test_a_thin_line_pulls_the_verdict(self):
        spec = self._spec(parameters=[with_changes(GAIN, sigma=1.5), POWER, NOISE])
        result = assess_design_principles(spec)
        self.assertEqual(result["verdict"], PARAMETRIC_MARGIN_SHORTFALL)

    def test_yield_shortfall_is_reported_when_every_line_is_thin(self):
        thin = [
            with_changes(GAIN, sigma=1.5, nominal=21.0),
            with_changes(POWER, sigma=1.2, nominal=29.0),
            with_changes(NOISE, sigma=1.0, nominal=3.0),
        ]
        result = assess_design_principles(
            self._spec(parameters=thin, policy={"required_margin_sigma": 0.0})
        )
        self.assertEqual(result["verdict"], PREDICTED_YIELD_SHORTFALL)

    def test_derating_breach_outranks_a_margin_shortfall(self):
        spec = self._spec(
            parameters=[with_changes(GAIN, sigma=1.5), POWER, NOISE],
            stresses=[with_changes(CHANNEL, applied=170.0), CURRENT, POWER_DENSITY],
        )
        result = assess_design_principles(spec)
        self.assertEqual(result["verdict"], DERATING_LIMIT_EXCEEDED)

    def test_open_design_rule_violations_are_reported(self):
        result = assess_design_principles(self._spec(drc_violations=3))
        self.assertEqual(result["verdict"], DESIGN_RULE_VIOLATIONS_OPEN)

    def test_novel_design_without_a_test_vehicle_is_flagged(self):
        result = assess_design_principles(self._spec(cells={"proven": 2, "total": 10}))
        self.assertEqual(result["verdict"], UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_planned_test_vehicle_answers_the_novelty_finding(self):
        result = assess_design_principles(
            self._spec(cells={"proven": 2, "total": 10}, test_vehicle_planned=True)
        )
        self.assertTrue(result["satisfied"])

    def test_proven_fraction_exactly_at_the_floor_is_accepted(self):
        result = assess_design_principles(self._spec(cells={"proven": 7, "total": 10}))
        self.assertAlmostEqual(result["proven_cell_fraction"], 0.70, places=9)
        self.assertTrue(result["satisfied"])

    def test_missing_on_wafer_structures_are_reported(self):
        result = assess_design_principles(self._spec(on_wafer_test_structures=False))
        self.assertEqual(result["verdict"], ON_WAFER_TEST_PROVISION_MISSING)

    def test_on_wafer_requirement_can_be_waived_by_policy(self):
        result = assess_design_principles(
            self._spec(
                on_wafer_test_structures=False,
                policy={"require_on_wafer_test_structures": False},
            )
        )
        self.assertTrue(result["satisfied"])

    def test_duplicate_parameter_identifier_rejected(self):
        spec = self._spec(parameters=[GAIN, with_changes(POWER, id="small-signal-gain-db")])
        with self.assertRaises(ValueError):
            assess_design_principles(spec)

    def test_negative_violation_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_principles(self._spec(drc_violations=-1))

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_principles(self._spec(parameters=[]))

    def test_missing_cells_key_rejected(self):
        spec = self._spec()
        del spec["cells"]
        with self.assertRaises(ValueError):
            assess_design_principles(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_principles(["parameters"])

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertAlmostEqual(MARGIN_TOLERANCE, 1e-9, places=12)
        self.assertAlmostEqual(math.erf(0.0), 0.0, places=12)


if __name__ == "__main__":
    unittest.main()
