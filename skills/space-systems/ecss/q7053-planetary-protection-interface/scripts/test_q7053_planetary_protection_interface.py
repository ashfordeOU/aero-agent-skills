"""Contract tests for the ECSS-Q-ST-70-53C planetary-protection interface."""

import copy
import unittest

from q7053_planetary_protection_interface_logic import (
    ALLOCATION_TOLERANCE,
    DRY_HEAT,
    PROCESSES,
    VAPOUR_PHASE,
    assess_planetary_protection_interface,
    dry_heat_d_value,
    effective_d_value,
    envelope_findings,
    log_reduction,
    required_exposure_minutes,
    surviving_bioburden,
    validate_process,
    vapour_phase_d_value,
)

DRY_HEAT_PARAMETERS = {
    "reference_d_minutes": 10.0,
    "reference_temperature_c": 125.0,
    "temperature_c": 125.0,
    "z_value_c": 21.0,
}

VAPOUR_PHASE_PARAMETERS = {
    "reference_d_minutes": 2.0,
    "reference_concentration_mg_l": 1.0,
    "concentration_mg_l": 1.0,
    "concentration_exponent": 1.0,
}

QUALIFIED_ENVELOPE = {
    "peak_temperature_c": 150.0,
    "cycles": 3.0,
    "accumulated_exposure_minutes": 240.0,
}


class ProcessTests(unittest.TestCase):
    def test_dry_heat_is_a_known_process(self):
        self.assertEqual(validate_process(DRY_HEAT), DRY_HEAT)

    def test_vapour_phase_is_a_known_process(self):
        self.assertEqual(validate_process(VAPOUR_PHASE), VAPOUR_PHASE)

    def test_both_processes_are_listed(self):
        self.assertEqual(len(PROCESSES), 2)

    def test_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            validate_process("gamma-irradiation")


class DecimalReductionTimeTests(unittest.TestCase):
    def test_reference_condition_returns_the_reference_value(self):
        self.assertAlmostEqual(dry_heat_d_value(10.0, 125.0, 125.0, 21.0), 10.0, places=9)

    def test_one_z_value_hotter_divides_the_time_by_ten(self):
        self.assertAlmostEqual(dry_heat_d_value(10.0, 125.0, 146.0, 21.0), 1.0, places=9)

    def test_one_z_value_cooler_multiplies_the_time_by_ten(self):
        self.assertAlmostEqual(dry_heat_d_value(10.0, 125.0, 104.0, 21.0), 100.0, places=9)

    def test_two_z_values_hotter_divides_the_time_by_a_hundred(self):
        self.assertAlmostEqual(dry_heat_d_value(10.0, 125.0, 167.0, 21.0), 0.1, places=9)

    def test_zero_z_value_rejected(self):
        with self.assertRaises(ValueError):
            dry_heat_d_value(10.0, 125.0, 146.0, 0.0)

    def test_non_positive_reference_time_rejected(self):
        with self.assertRaises(ValueError):
            dry_heat_d_value(0.0, 125.0, 146.0, 21.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            dry_heat_d_value(10.0, 125.0, -300.0, 21.0)

    def test_vapour_phase_reference_condition_returns_the_reference_value(self):
        self.assertAlmostEqual(vapour_phase_d_value(2.0, 1.0, 1.0, 1.0), 2.0, places=9)

    def test_doubling_the_concentration_halves_the_time_at_unit_exponent(self):
        self.assertAlmostEqual(vapour_phase_d_value(2.0, 1.0, 2.0, 1.0), 1.0, places=9)

    def test_a_squared_exponent_quarters_the_time(self):
        self.assertAlmostEqual(vapour_phase_d_value(2.0, 1.0, 2.0, 2.0), 0.5, places=9)

    def test_zero_concentration_rejected(self):
        with self.assertRaises(ValueError):
            vapour_phase_d_value(2.0, 1.0, 0.0, 1.0)

    def test_dispatch_selects_the_dry_heat_relation(self):
        parameters = dict(DRY_HEAT_PARAMETERS, temperature_c=146.0)
        self.assertAlmostEqual(effective_d_value(DRY_HEAT, parameters), 1.0, places=9)

    def test_dispatch_selects_the_vapour_phase_relation(self):
        parameters = dict(VAPOUR_PHASE_PARAMETERS, concentration_mg_l=2.0)
        self.assertAlmostEqual(effective_d_value(VAPOUR_PHASE, parameters), 1.0, places=9)

    def test_dispatch_rejects_missing_dry_heat_parameters(self):
        parameters = dict(DRY_HEAT_PARAMETERS)
        del parameters["z_value_c"]
        with self.assertRaises(ValueError):
            effective_d_value(DRY_HEAT, parameters)

    def test_dispatch_rejects_missing_vapour_phase_parameters(self):
        parameters = dict(VAPOUR_PHASE_PARAMETERS)
        del parameters["concentration_exponent"]
        with self.assertRaises(ValueError):
            effective_d_value(VAPOUR_PHASE, parameters)

    def test_dispatch_rejects_a_non_mapping(self):
        with self.assertRaises(ValueError):
            effective_d_value(DRY_HEAT, ["reference_d_minutes"])


class ReductionArithmeticTests(unittest.TestCase):
    def test_six_decimal_reductions_from_six_d_values(self):
        self.assertAlmostEqual(log_reduction(60.0, 10.0), 6.0, places=9)

    def test_no_exposure_gives_no_reduction(self):
        self.assertAlmostEqual(log_reduction(0.0, 10.0), 0.0, places=9)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            log_reduction(-1.0, 10.0)

    def test_zero_decimal_reduction_time_rejected(self):
        with self.assertRaises(ValueError):
            log_reduction(60.0, 0.0)

    def test_six_reductions_leave_one_spore_in_a_million(self):
        self.assertAlmostEqual(surviving_bioburden(1.0e6, 6.0), 1.0, places=9)

    def test_three_reductions_leave_a_thousandth(self):
        self.assertAlmostEqual(surviving_bioburden(1.0e6, 3.0), 1000.0, places=6)

    def test_no_reduction_leaves_the_initial_count(self):
        self.assertAlmostEqual(surviving_bioburden(1.0e6, 0.0), 1.0e6, places=6)

    def test_surviving_count_never_reaches_zero(self):
        self.assertGreater(surviving_bioburden(1.0e6, 12.0), 0.0)

    def test_negative_reduction_rejected(self):
        with self.assertRaises(ValueError):
            surviving_bioburden(1.0e6, -1.0)

    def test_required_exposure_is_the_time_per_decade_times_the_target(self):
        self.assertAlmostEqual(required_exposure_minutes(10.0, 6.0), 60.0, places=9)

    def test_zero_target_needs_no_exposure(self):
        self.assertAlmostEqual(required_exposure_minutes(10.0, 0.0), 0.0, places=9)

    def test_required_exposure_rejects_a_zero_decimal_reduction_time(self):
        with self.assertRaises(ValueError):
            required_exposure_minutes(0.0, 6.0)


class EnvelopeTests(unittest.TestCase):
    def test_a_request_inside_the_envelope_has_no_findings(self):
        required = {"peak_temperature_c": 146.0, "cycles": 2.0,
                    "accumulated_exposure_minutes": 120.0}
        self.assertEqual(envelope_findings(required, QUALIFIED_ENVELOPE), [])

    def test_a_request_exactly_on_a_ceiling_is_inside(self):
        required = {"peak_temperature_c": 150.0}
        self.assertEqual(envelope_findings(required, QUALIFIED_ENVELOPE), [])

    def test_a_request_over_a_ceiling_is_reported(self):
        required = {"peak_temperature_c": 165.0}
        findings = envelope_findings(required, QUALIFIED_ENVELOPE)
        self.assertEqual(len(findings), 1)
        self.assertIn("qualified ceiling", findings[0])

    def test_a_parameter_the_envelope_never_covered_is_outside_it(self):
        required = {"sterilant_concentration_mg_l": 6.0}
        findings = envelope_findings(required, QUALIFIED_ENVELOPE)
        self.assertEqual(len(findings), 1)
        self.assertIn("not covered", findings[0])

    def test_several_breaches_are_each_reported(self):
        required = {"peak_temperature_c": 165.0, "cycles": 5.0}
        self.assertEqual(len(envelope_findings(required, QUALIFIED_ENVELOPE)), 2)

    def test_empty_required_envelope_rejected(self):
        with self.assertRaises(ValueError):
            envelope_findings({}, QUALIFIED_ENVELOPE)

    def test_empty_qualified_envelope_rejected(self):
        with self.assertRaises(ValueError):
            envelope_findings({"cycles": 1.0}, {})

    def test_negative_required_value_rejected(self):
        with self.assertRaises(ValueError):
            envelope_findings({"cycles": -1.0}, QUALIFIED_ENVELOPE)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "item_id": "BRACKET-5501-polymer-insert",
            "process": DRY_HEAT,
            "process_parameters": dict(DRY_HEAT_PARAMETERS, temperature_c=146.0),
            "exposure_minutes": 60.0,
            "initial_bioburden_spores": 1.0e6,
            "allocated_bioburden_spores": 300.0,
            "target_log_reduction": 4.0,
            "required_envelope": {"peak_temperature_c": 146.0, "cycles": 2.0,
                                  "accumulated_exposure_minutes": 120.0},
            "qualified_envelope": copy.deepcopy(QUALIFIED_ENVELOPE),
        }
        spec.update(overrides)
        return spec

    def test_a_compliant_interface_has_no_findings(self):
        result = assess_planetary_protection_interface(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_the_corrected_decimal_reduction_time_is_reported(self):
        result = assess_planetary_protection_interface(self._spec())
        self.assertAlmostEqual(result["effective_d_minutes"], 1.0, places=9)

    def test_the_achieved_reduction_follows_the_corrected_time(self):
        result = assess_planetary_protection_interface(self._spec())
        self.assertAlmostEqual(result["achieved_log_reduction"], 60.0, places=9)

    def test_item_id_is_carried_through(self):
        result = assess_planetary_protection_interface(self._spec())
        self.assertEqual(result["item_id"], "BRACKET-5501-polymer-insert")

    def test_an_allocation_breach_is_reported(self):
        spec = self._spec(exposure_minutes=2.0, allocated_bioburden_spores=300.0)
        result = assess_planetary_protection_interface(spec)
        self.assertAlmostEqual(result["surviving_bioburden_spores"], 10000.0, places=6)
        self.assertFalse(result["allocation_met"])

    def test_the_surviving_count_exactly_on_the_allocation_is_met(self):
        spec = self._spec(exposure_minutes=3.0, allocated_bioburden_spores=1000.0,
                          target_log_reduction=3.0)
        result = assess_planetary_protection_interface(spec)
        self.assertAlmostEqual(result["surviving_bioburden_spores"], 1000.0, places=6)
        self.assertTrue(result["allocation_met"])

    def test_a_reduction_shortfall_names_the_extra_exposure_needed(self):
        spec = self._spec(exposure_minutes=2.0, target_log_reduction=6.0,
                          allocated_bioburden_spores=1.0e6)
        result = assess_planetary_protection_interface(spec)
        self.assertFalse(result["target_met"])
        self.assertAlmostEqual(result["required_exposure_minutes"], 6.0, places=9)
        self.assertAlmostEqual(result["exposure_shortfall_minutes"], 4.0, places=9)

    def test_a_target_exactly_achieved_is_met(self):
        spec = self._spec(exposure_minutes=4.0, target_log_reduction=4.0,
                          allocated_bioburden_spores=1.0e6)
        result = assess_planetary_protection_interface(spec)
        self.assertTrue(result["target_met"])
        self.assertAlmostEqual(result["exposure_shortfall_minutes"], 0.0, places=9)

    def test_no_target_leaves_the_derivation_absent(self):
        spec = self._spec()
        del spec["target_log_reduction"]
        result = assess_planetary_protection_interface(spec)
        self.assertIsNone(result["required_exposure_minutes"])
        self.assertTrue(result["target_met"])

    def test_leaving_the_qualified_envelope_rejects_a_passing_reduction(self):
        spec = self._spec()
        spec["required_envelope"]["peak_temperature_c"] = 165.0
        result = assess_planetary_protection_interface(spec)
        self.assertTrue(result["allocation_met"])
        self.assertFalse(result["within_qualified_envelope"])
        self.assertFalse(result["acceptable"])

    def test_a_vapour_phase_interface_uses_the_concentration_relation(self):
        spec = self._spec(
            process=VAPOUR_PHASE,
            process_parameters=dict(VAPOUR_PHASE_PARAMETERS, concentration_mg_l=2.0),
            exposure_minutes=6.0,
            target_log_reduction=6.0,
        )
        result = assess_planetary_protection_interface(spec)
        self.assertAlmostEqual(result["effective_d_minutes"], 1.0, places=9)
        self.assertTrue(result["target_met"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["qualified_envelope"]
        with self.assertRaises(ValueError):
            assess_planetary_protection_interface(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_planetary_protection_interface(["process"])

    def test_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            assess_planetary_protection_interface(self._spec(process="autoclave"))

    def test_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            assess_planetary_protection_interface(
                self._spec(allocated_bioburden_spores=-1.0)
            )

    def test_allocation_tolerance_is_small_and_positive(self):
        self.assertGreater(ALLOCATION_TOLERANCE, 0.0)
        self.assertLess(ALLOCATION_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
