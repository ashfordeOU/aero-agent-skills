"""Contract tests for the clause 4.5.2.2 CCS verification logic."""

import unittest

from e31_cryogenic_control_system_ccs_verification_logic import (
    LEVELS,
    METHODS,
    MARGIN_TOLERANCE,
    assess_ccs_verification,
    cooldown_slack_h,
    evaluate_objective,
    grade_setup,
    heat_lift_margin,
    level_rank,
    objective_coverage,
    parasitic_load_rollup,
    stability_compliant,
    temperature_stability_pp_k,
    validate_level,
    validate_method,
    validate_temperature_k,
)

AGREED_SETUP = {
    "sink_temperature_k": 100.0,
    "chamber_pressure_pa": 1.0e-3,
    "boundary_simulator": True,
}

ACHIEVED_SETUP = {
    "sink_temperature_k": 92.0,
    "chamber_pressure_pa": 4.0e-4,
    "boundary_simulator": True,
}


def _objective(oid, quantity, agreed_level="instrument", closed_level="instrument",
               agreed_method="test", closed_method="test"):
    return {
        "id": oid,
        "quantity": quantity,
        "agreed_level": agreed_level,
        "closed_level": closed_level,
        "agreed_method": agreed_method,
        "closed_method": closed_method,
    }


class LevelAndMethodTests(unittest.TestCase):
    def test_instrument_is_the_most_detailed_level(self):
        self.assertEqual(level_rank("instrument"), 0)
        self.assertLess(level_rank("instrument"), level_rank("subsystem"))

    def test_level_name_is_normalised(self):
        self.assertEqual(validate_level(" Subsystem "), "subsystem")

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level("spacecraft")

    def test_non_string_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level(2)

    def test_method_name_is_normalised(self):
        self.assertEqual(validate_method("ANALYSIS"), "analysis")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_method("inspection-by-eye")

    def test_level_and_method_vocabularies_are_ordered(self):
        self.assertEqual(LEVELS[0], "instrument")
        self.assertEqual(METHODS[0], "test")


class TemperatureTests(unittest.TestCase):
    def test_kelvin_returned_as_float(self):
        self.assertAlmostEqual(validate_temperature_k(77, "sample"), 77.0)

    def test_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(0.0, "sample")

    def test_negative_kelvin_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(-5.0, "sample")

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(True, "sample")

    def test_non_finite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(float("nan"), "sample")


class HeatLiftTests(unittest.TestCase):
    def test_margin_is_fractional(self):
        self.assertAlmostEqual(heat_lift_margin(1.2, 1.0), 0.2, places=9)

    def test_exact_duty_gives_zero_margin(self):
        self.assertAlmostEqual(heat_lift_margin(0.8, 0.8), 0.0, places=9)

    def test_shortfall_is_negative(self):
        self.assertAlmostEqual(heat_lift_margin(0.75, 1.0), -0.25, places=9)

    def test_zero_required_duty_rejected(self):
        with self.assertRaises(ValueError):
            heat_lift_margin(1.0, 0.0)

    def test_negative_available_lift_rejected(self):
        with self.assertRaises(ValueError):
            heat_lift_margin(-0.1, 1.0)


class StabilityTests(unittest.TestCase):
    def test_peak_to_peak_of_window(self):
        self.assertAlmostEqual(temperature_stability_pp_k([40.0, 40.05, 39.98]), 0.07, places=9)

    def test_single_reading_is_not_a_window(self):
        with self.assertRaises(ValueError):
            temperature_stability_pp_k([40.0])

    def test_excursion_inside_allowance_conforms(self):
        self.assertTrue(stability_compliant(0.05, 0.1))

    def test_excursion_exactly_on_the_allowance_conforms(self):
        self.assertTrue(stability_compliant(0.1, 0.1))

    def test_excursion_above_allowance_fails(self):
        self.assertFalse(stability_compliant(0.2, 0.1))

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            stability_compliant(0.05, -0.1)


class CooldownTests(unittest.TestCase):
    def test_faster_run_has_positive_slack(self):
        self.assertAlmostEqual(cooldown_slack_h(10.0, 12.0), 2.0, places=9)

    def test_overrun_has_negative_slack(self):
        self.assertAlmostEqual(cooldown_slack_h(14.5, 12.0), -2.5, places=9)

    def test_zero_agreed_duration_rejected(self):
        with self.assertRaises(ValueError):
            cooldown_slack_h(10.0, 0.0)


class ParasiticTests(unittest.TestCase):
    def test_total_and_dominant_path(self):
        result = parasitic_load_rollup(
            {"harness": 0.12, "struts": 0.30, "radiation": 0.08}, 0.6
        )
        self.assertAlmostEqual(result["total_w"], 0.5, places=9)
        self.assertEqual(result["dominant_path"], "struts")
        self.assertTrue(result["within_allocation"])

    def test_total_exactly_on_allocation_is_within(self):
        result = parasitic_load_rollup({"harness": 0.25, "struts": 0.25}, 0.5)
        self.assertTrue(result["within_allocation"])

    def test_overspend_is_flagged(self):
        result = parasitic_load_rollup({"harness": 0.4, "struts": 0.4}, 0.5)
        self.assertFalse(result["within_allocation"])

    def test_zero_load_path_allowed(self):
        result = parasitic_load_rollup({"harness": 0.0, "struts": 0.2}, 0.5)
        self.assertAlmostEqual(result["total_w"], 0.2, places=9)

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_load_rollup({}, 0.5)

    def test_negative_load_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_load_rollup({"harness": -0.1}, 0.5)


class SetupTests(unittest.TestCase):
    def test_conforming_setup(self):
        result = grade_setup(ACHIEVED_SETUP, AGREED_SETUP)
        self.assertTrue(result["setup_conforms"])
        self.assertEqual(result["findings"], [])

    def test_warm_sink_is_a_finding(self):
        achieved = dict(ACHIEVED_SETUP, sink_temperature_k=140.0)
        result = grade_setup(achieved, AGREED_SETUP)
        self.assertFalse(result["setup_conforms"])

    def test_sink_exactly_at_the_agreed_value_conforms(self):
        achieved = dict(ACHIEVED_SETUP, sink_temperature_k=100.0)
        self.assertTrue(grade_setup(achieved, AGREED_SETUP)["setup_conforms"])

    def test_poor_vacuum_is_a_finding(self):
        achieved = dict(ACHIEVED_SETUP, chamber_pressure_pa=1.0e-2)
        self.assertFalse(grade_setup(achieved, AGREED_SETUP)["setup_conforms"])

    def test_missing_boundary_simulator_is_a_finding(self):
        achieved = dict(ACHIEVED_SETUP, boundary_simulator=False)
        result = grade_setup(achieved, AGREED_SETUP)
        self.assertFalse(result["setup_conforms"])
        self.assertEqual(len(result["findings"]), 1)

    def test_setup_without_pressure_key_rejected(self):
        with self.assertRaises(ValueError):
            grade_setup({"sink_temperature_k": 90.0}, AGREED_SETUP)


class ObjectiveTests(unittest.TestCase):
    def test_matching_level_and_method_conforms(self):
        record = evaluate_objective(_objective("VO-1", "heat-lift"))
        self.assertTrue(record["conforms"])

    def test_more_detailed_level_may_close_a_coarser_objective(self):
        record = evaluate_objective(
            _objective("VO-2", "stability", agreed_level="subsystem",
                       closed_level="instrument")
        )
        self.assertTrue(record["conforms"])

    def test_coarser_level_cannot_close_an_instrument_objective(self):
        record = evaluate_objective(
            _objective("VO-3", "stability", agreed_level="instrument",
                       closed_level="subsystem")
        )
        self.assertFalse(record["conforms"])

    def test_analysis_cannot_close_an_agreed_test(self):
        record = evaluate_objective(
            _objective("VO-4", "cooldown", agreed_method="test", closed_method="analysis")
        )
        self.assertFalse(record["conforms"])

    def test_test_may_close_an_agreed_analysis(self):
        record = evaluate_objective(
            _objective("VO-5", "parasitics", agreed_method="analysis", closed_method="test")
        )
        self.assertTrue(record["conforms"])

    def test_two_deviations_give_two_findings(self):
        record = evaluate_objective(
            _objective("VO-6", "stability", agreed_level="instrument",
                       closed_level="subsystem", agreed_method="test",
                       closed_method="review-of-design")
        )
        self.assertEqual(len(record["findings"]), 2)

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_objective(_objective("  ", "heat-lift"))

    def test_missing_key_rejected(self):
        bad = _objective("VO-7", "heat-lift")
        del bad["closed_method"]
        with self.assertRaises(ValueError):
            evaluate_objective(bad)


class CoverageTests(unittest.TestCase):
    def test_all_quantities_covered(self):
        records = [evaluate_objective(_objective("VO-1", "heat-lift"))]
        self.assertEqual(objective_coverage(records, ["heat-lift"]), [])

    def test_non_conforming_objective_does_not_cover(self):
        records = [
            evaluate_objective(
                _objective("VO-1", "heat-lift", agreed_level="instrument",
                           closed_level="subsystem")
            )
        ]
        self.assertEqual(objective_coverage(records, ["heat-lift"]), ["heat-lift"])

    def test_empty_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            objective_coverage([], [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "objectives": [
                _objective("VO-1", "heat-lift"),
                _objective("VO-2", "stability"),
                _objective("VO-3", "cooldown", agreed_method="analysis",
                           closed_method="analysis"),
                _objective("VO-4", "parasitics", agreed_level="subsystem",
                           closed_level="subsystem", agreed_method="analysis",
                           closed_method="analysis"),
            ],
            "required_quantities": ["heat-lift", "stability", "cooldown", "parasitics"],
            "agreed_setup": AGREED_SETUP,
            "achieved_setup": ACHIEVED_SETUP,
            "lift_available_w": 1.1,
            "lift_required_w": 1.0,
            "stability_samples_k": [39.98, 40.0, 40.03],
            "stability_allowed_k": 0.1,
            "cooldown_measured_h": 9.5,
            "cooldown_agreed_h": 12.0,
            "parasitic_loads_w": {"harness": 0.12, "struts": 0.30, "radiation": 0.08},
            "parasitic_allocation_w": 0.6,
        }
        spec.update(overrides)
        return spec

    def test_nominal_campaign_is_verified(self):
        result = assess_ccs_verification(self._spec())
        self.assertTrue(result["verified"])
        self.assertEqual(result["findings"], [])

    def test_heat_lift_shortfall_fails_the_campaign(self):
        result = assess_ccs_verification(self._spec(lift_available_w=0.8))
        self.assertFalse(result["verified"])
        self.assertFalse(result["heat_lift_compliant"])

    def test_heat_lift_exactly_on_duty_still_passes(self):
        result = assess_ccs_verification(self._spec(lift_available_w=1.0, lift_required_w=1.0))
        self.assertTrue(result["heat_lift_compliant"])
        self.assertAlmostEqual(result["heat_lift_margin"], 0.0, places=9)

    def test_stability_breach_is_reported(self):
        result = assess_ccs_verification(
            self._spec(stability_samples_k=[39.5, 40.0, 40.4])
        )
        self.assertFalse(result["stability_compliant"])
        self.assertFalse(result["verified"])

    def test_cooldown_overrun_is_reported(self):
        result = assess_ccs_verification(self._spec(cooldown_measured_h=15.0))
        self.assertAlmostEqual(result["cooldown_slack_h"], -3.0, places=9)
        self.assertFalse(result["verified"])

    def test_uncovered_quantity_is_reported(self):
        result = assess_ccs_verification(
            self._spec(required_quantities=["heat-lift", "stability", "cooldown",
                                            "parasitics", "cold-tip-contamination"])
        )
        self.assertIn("cold-tip-contamination", result["uncovered_quantities"])
        self.assertFalse(result["verified"])

    def test_setup_deviation_propagates_to_the_rollup(self):
        result = assess_ccs_verification(
            self._spec(achieved_setup=dict(ACHIEVED_SETUP, sink_temperature_k=150.0))
        )
        self.assertFalse(result["setup"]["setup_conforms"])
        self.assertFalse(result["verified"])

    def test_duplicate_objective_id_rejected(self):
        spec = self._spec()
        spec["objectives"] = list(spec["objectives"]) + [_objective("VO-1", "heat-lift")]
        with self.assertRaises(ValueError):
            assess_ccs_verification(spec)

    def test_empty_objective_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_ccs_verification(self._spec(objectives=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["agreed_setup"]
        with self.assertRaises(ValueError):
            assess_ccs_verification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ccs_verification(["objectives"])

    def test_tolerance_is_small_enough_to_relax_nothing(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
