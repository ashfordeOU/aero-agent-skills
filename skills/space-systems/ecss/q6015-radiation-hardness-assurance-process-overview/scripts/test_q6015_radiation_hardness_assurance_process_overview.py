"""Contract tests for the clause 4.1 hardness assurance flow logic."""

import unittest

from q6015_radiation_hardness_assurance_process_overview_logic import (
    DEFAULT_REQUIRED_MARGIN,
    ENVIRONMENT_QUANTITIES,
    MARGIN_TOLERANCE,
    MIN_DESIGN_FACTOR,
    RHA_STAGES,
    assess_assurance_flow,
    assess_stage_sequence,
    assess_part,
    design_margin,
    local_environment_level,
    margin_holds,
    normalize_token,
    specified_level,
    stage_completeness,
    validate_dose_depth_curve,
    validate_environment,
    validate_quantity,
    validate_stage,
)

CURVE = [
    (1.0, 40000.0),
    (2.0, 10000.0),
    (4.0, 2500.0),
    (8.0, 625.0),
]

ENVIRONMENT = {
    "quantity": "total-ionising-dose",
    "reference_thickness_mm": 1.0,
    "level": 40000.0,
    "mission_years": 5.0,
}


def _part(**overrides):
    part = {
        "part_number": "RH-2210-C",
        "local_shielding_mm": 4.0,
        "design_factor": 2.0,
        "capability": 20000.0,
    }
    part.update(overrides)
    return part


def _flow(**overrides):
    flow = {
        "environment": dict(ENVIRONMENT),
        "dose_depth_curve": [tuple(p) for p in CURVE],
        "stages": list(RHA_STAGES),
        "parts": [_part()],
    }
    flow.update(overrides)
    return flow


class QuantityAndStageTests(unittest.TestCase):
    def test_recognized_quantities_validate(self):
        for quantity in ENVIRONMENT_QUANTITIES:
            self.assertEqual(validate_quantity(quantity), quantity)

    def test_unknown_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_quantity("proton-flux")

    def test_normalize_token_folds_case_and_underscores(self):
        self.assertEqual(
            normalize_token("Total_Ionising_Dose"), "total-ionising-dose"
        )

    def test_unknown_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage("procurement-kickoff")

    def test_duplicate_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_stage_sequence(list(RHA_STAGES) + ["design-margin-evaluation"])

    def test_canonical_flow_is_complete_and_in_order(self):
        assessment = assess_stage_sequence(list(RHA_STAGES))
        self.assertEqual(assessment["absent_stages"], [])
        self.assertTrue(assessment["in_order"])

    def test_absent_stages_are_named_individually(self):
        declared = [s for s in RHA_STAGES
                    if s not in ("shielding-and-geometry-analysis",
                                 "lot-radiation-verification-testing")]
        assessment = assess_stage_sequence(declared)
        self.assertEqual(
            assessment["absent_stages"],
            ["shielding-and-geometry-analysis",
             "lot-radiation-verification-testing"],
        )

    def test_margin_evaluation_before_specified_levels_is_out_of_order(self):
        declared = [
            "mission-environment-definition",
            "design-margin-evaluation",
            "part-level-specified-levels",
        ]
        assessment = assess_stage_sequence(declared)
        self.assertFalse(assessment["in_order"])
        self.assertEqual(len(assessment["order_findings"]), 1)

    def test_full_flow_completeness_is_unity(self):
        self.assertAlmostEqual(stage_completeness(list(RHA_STAGES)), 1.0, places=9)

    def test_partial_flow_completeness_is_the_counted_fraction(self):
        declared = list(RHA_STAGES)[:-2]
        expected = (len(RHA_STAGES) - 2) / float(len(RHA_STAGES))
        self.assertAlmostEqual(stage_completeness(declared), expected, places=9)

    def test_stage_sequence_requires_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_stage_sequence("mission-environment-definition")


class EnvironmentTests(unittest.TestCase):
    def test_valid_environment_is_returned_as_floats(self):
        env = validate_environment(dict(ENVIRONMENT))
        self.assertAlmostEqual(env["level"], 40000.0, places=9)
        self.assertAlmostEqual(env["mission_years"], 5.0, places=9)

    def test_missing_environment_key_is_rejected(self):
        bad = dict(ENVIRONMENT)
        del bad["mission_years"]
        with self.assertRaises(ValueError):
            validate_environment(bad)

    def test_zero_environment_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(dict(ENVIRONMENT, level=0.0))

    def test_negative_reference_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(dict(ENVIRONMENT, reference_thickness_mm=-1.0))

    def test_boolean_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(dict(ENVIRONMENT, level=True))

    def test_non_mapping_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(["total-ionising-dose"])


class CurveTests(unittest.TestCase):
    def test_valid_curve_is_returned_point_for_point(self):
        points = validate_dose_depth_curve([tuple(p) for p in CURVE])
        self.assertEqual(len(points), len(CURVE))

    def test_single_point_curve_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 40000.0)])

    def test_curve_with_descending_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(4.0, 2500.0), (2.0, 10000.0)])

    def test_curve_whose_level_rises_with_shielding_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 100.0), (2.0, 200.0)])

    def test_malformed_curve_point_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_dose_depth_curve([(1.0, 40000.0), (2.0,)])

    def test_tabulated_thickness_returns_its_own_level_exactly(self):
        self.assertAlmostEqual(
            local_environment_level(CURVE, 2.0), 10000.0, places=9
        )

    def test_interpolated_point_falls_between_its_neighbours(self):
        value = local_environment_level(CURVE, 3.0)
        self.assertLess(value, 10000.0)
        self.assertGreater(value, 2500.0)

    def test_interpolation_is_log_log_on_a_power_law_curve(self):
        # The curve halves thickness-decade for decade, so the midpoint in log
        # thickness lands on the geometric mean of the bracketing levels.
        value = local_environment_level(CURVE, 2.0 * (2.0 ** 0.5))
        self.assertAlmostEqual(value, (10000.0 * 2500.0) ** 0.5, places=6)

    def test_thickness_below_the_curve_span_is_refused(self):
        with self.assertRaises(ValueError):
            local_environment_level(CURVE, 0.5)

    def test_thickness_above_the_curve_span_is_refused(self):
        with self.assertRaises(ValueError):
            local_environment_level(CURVE, 12.0)


class MarginTests(unittest.TestCase):
    def test_specified_level_applies_the_design_factor(self):
        self.assertAlmostEqual(specified_level(2500.0, 2.0), 5000.0, places=9)

    def test_unit_design_factor_is_allowed(self):
        self.assertAlmostEqual(
            specified_level(2500.0, MIN_DESIGN_FACTOR), 2500.0, places=9
        )

    def test_design_factor_below_unity_is_refused(self):
        with self.assertRaises(ValueError):
            specified_level(2500.0, 0.5)

    def test_margin_is_capability_over_specified_level(self):
        self.assertAlmostEqual(design_margin(20000.0, 5000.0), 4.0, places=9)

    def test_zero_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            design_margin(0.0, 5000.0)

    def test_margin_exactly_at_the_requirement_holds(self):
        self.assertTrue(margin_holds(2.0, 2.0))

    def test_margin_just_below_the_requirement_does_not_hold(self):
        self.assertFalse(margin_holds(1.9, 2.0))

    def test_margin_tolerance_is_small_and_positive(self):
        self.assertGreater(MARGIN_TOLERANCE, 0.0)
        self.assertLess(MARGIN_TOLERANCE, 1e-6)

    def test_default_required_margin_exceeds_unity(self):
        self.assertGreater(DEFAULT_REQUIRED_MARGIN, 1.0)


class PartTests(unittest.TestCase):
    def test_part_is_carried_from_environment_to_margin(self):
        assessed = assess_part(_part(), CURVE, ENVIRONMENT)
        self.assertAlmostEqual(assessed["local_level"], 2500.0, places=9)
        self.assertAlmostEqual(assessed["specified_level"], 5000.0, places=9)
        self.assertAlmostEqual(assessed["margin"], 4.0, places=9)
        self.assertTrue(assessed["margin_holds"])

    def test_thinner_local_shielding_raises_the_specified_level(self):
        thin = assess_part(_part(local_shielding_mm=2.0), CURVE, ENVIRONMENT)
        thick = assess_part(_part(local_shielding_mm=8.0), CURVE, ENVIRONMENT)
        self.assertGreater(thin["specified_level"], thick["specified_level"])

    def test_part_exactly_on_its_required_margin_passes(self):
        assessed = assess_part(
            _part(capability=10000.0), CURVE, ENVIRONMENT, required_margin=2.0
        )
        self.assertAlmostEqual(assessed["margin"], 2.0, places=9)
        self.assertTrue(assessed["margin_holds"])
        self.assertEqual(assessed["findings"], [])

    def test_short_margin_becomes_a_finding(self):
        assessed = assess_part(
            _part(capability=6000.0), CURVE, ENVIRONMENT, required_margin=2.0
        )
        self.assertFalse(assessed["margin_holds"])
        self.assertEqual(len(assessed["findings"]), 1)

    def test_part_missing_a_required_key_is_rejected(self):
        bad = _part()
        del bad["design_factor"]
        with self.assertRaises(ValueError):
            assess_part(bad, CURVE, ENVIRONMENT)

    def test_part_outside_the_curve_span_is_refused_not_extrapolated(self):
        with self.assertRaises(ValueError):
            assess_part(_part(local_shielding_mm=20.0), CURVE, ENVIRONMENT)

    def test_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part("RH-2210-C", CURVE, ENVIRONMENT)


class FlowTests(unittest.TestCase):
    def test_complete_flow_is_acceptable(self):
        result = assess_assurance_flow(_flow())
        self.assertTrue(result["flow_acceptable"])
        self.assertAlmostEqual(result["stage_completeness"], 1.0, places=9)

    def test_absent_stage_reaches_the_verdict(self):
        stages = [s for s in RHA_STAGES if s != "lot-radiation-verification-testing"]
        result = assess_assurance_flow(_flow(stages=stages))
        self.assertFalse(result["flow_acceptable"])

    def test_worst_case_part_is_the_one_with_the_lowest_margin(self):
        result = assess_assurance_flow(
            _flow(
                parts=[
                    _part(),
                    _part(part_number="RH-3040-D", capability=11000.0),
                ]
            )
        )
        self.assertEqual(result["worst_case_part"], "RH-3040-D")
        self.assertAlmostEqual(result["worst_case_margin"], 2.2, places=9)

    def test_part_carried_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assurance_flow(_flow(parts=[_part(), _part()]))

    def test_empty_part_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assurance_flow(_flow(parts=[]))

    def test_flow_missing_a_required_key_is_rejected(self):
        bad = _flow()
        del bad["dose_depth_curve"]
        with self.assertRaises(ValueError):
            assess_assurance_flow(bad)

    def test_non_mapping_flow_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assurance_flow(["environment"])

    def test_project_margin_overrides_the_default(self):
        result = assess_assurance_flow(_flow(required_margin=5.0))
        self.assertFalse(result["flow_acceptable"])
        self.assertAlmostEqual(result["parts"][0]["required_margin"], 5.0, places=9)

    def test_every_finding_is_named_not_only_the_first(self):
        stages = [s for s in RHA_STAGES
                  if s not in ("shielding-and-geometry-analysis",
                               "mitigation-and-rework-decision")]
        result = assess_assurance_flow(
            _flow(
                stages=stages,
                parts=[
                    _part(capability=3000.0),
                    _part(part_number="RH-3040-D", capability=4000.0),
                ],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()
