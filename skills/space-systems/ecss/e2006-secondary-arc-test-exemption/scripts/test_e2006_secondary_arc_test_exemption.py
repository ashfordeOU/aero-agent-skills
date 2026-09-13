#!/usr/bin/env python3
"""Contract test for the clause 7.2.3.1 secondary-arc test exemption logic."""

import unittest

from e2006_secondary_arc_test_exemption_logic import (
    MINIMUM_ONSET_VOLTAGE_V,
    REQUIRED_EVIDENCE_ITEMS,
    SUSTAINING_CURRENT_LIMIT_A,
    evaluate_current_criterion,
    evaluate_secondary_arc_test_exemption,
    evaluate_voltage_criterion,
    missing_exemption_evidence,
    required_actions_on_refusal,
    sustained_arc_onset_voltage,
    worst_case_string_to_string_voltage,
)

FULL_EVIDENCE = list(REQUIRED_EVIDENCE_ITEMS)


def low_voltage_record(**overrides):
    record = {
        "nominal_operating_v": 28.0,
        "open_circuit_factor": 1.10,
        "temperature_coefficient_per_c": 0.0015,
        "minimum_temperature_c": -20.0,
        "reference_temperature_c": 20.0,
        "regulation_transient_v": 0.5,
        "conductor_gap_mm": 0.90,
        "insulation_material": "polyimide",
        "string_current_a": 0.12,
        "parallel_strings": 3,
        "evidence": list(FULL_EVIDENCE),
    }
    record.update(overrides)
    return record


class WorstCaseVoltageTests(unittest.TestCase):
    def test_nominal_only_returns_the_operating_point(self):
        value = worst_case_string_to_string_voltage(28.0)
        self.assertAlmostEqual(value, 28.0, places=9)

    def test_open_circuit_factor_scales_the_operating_point(self):
        value = worst_case_string_to_string_voltage(28.0, open_circuit_factor=1.25)
        self.assertAlmostEqual(value, 35.0, places=9)

    def test_cold_excursion_raises_the_worst_case(self):
        warm = worst_case_string_to_string_voltage(28.0, 1.25, 0.002, 20.0, 20.0, 0.0)
        cold = worst_case_string_to_string_voltage(28.0, 1.25, 0.002, -80.0, 20.0, 0.0)
        self.assertGreater(cold, warm)
        self.assertAlmostEqual(cold, 35.0 + 35.0 * 0.002 * 100.0, places=9)

    def test_regulation_transient_adds_directly(self):
        value = worst_case_string_to_string_voltage(
            28.0, 1.25, 0.0, 20.0, 20.0, regulation_transient_v=4.0
        )
        self.assertAlmostEqual(value, 39.0, places=9)

    def test_zero_nominal_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage(0.0)

    def test_open_circuit_factor_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage(28.0, open_circuit_factor=0.9)

    def test_negative_temperature_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage(28.0, 1.1, -0.002, -20.0, 20.0, 0.0)

    def test_minimum_above_reference_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage(28.0, 1.1, 0.002, 40.0, 20.0, 0.0)

    def test_negative_transient_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage(28.0, 1.1, 0.002, -20.0, 20.0, -1.0)

    def test_non_numeric_nominal_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_string_to_string_voltage("28")


class OnsetVoltageTests(unittest.TestCase):
    def test_reference_gap_and_polyimide_return_the_base_onset(self):
        self.assertAlmostEqual(sustained_arc_onset_voltage(0.90, "polyimide"), 50.0, places=9)

    def test_wider_gap_raises_the_onset(self):
        narrow = sustained_arc_onset_voltage(0.90, "polyimide")
        wide = sustained_arc_onset_voltage(1.90, "polyimide")
        self.assertAlmostEqual(wide - narrow, 22.0, places=9)

    def test_material_factor_is_applied(self):
        polyimide = sustained_arc_onset_voltage(0.90, "polyimide")
        composite = sustained_arc_onset_voltage(0.90, "bare-composite")
        self.assertLess(composite, polyimide)
        self.assertAlmostEqual(composite, 50.0 * 0.78, places=9)

    def test_material_name_is_case_insensitive(self):
        self.assertAlmostEqual(
            sustained_arc_onset_voltage(0.90, "Polyimide"), 50.0, places=9
        )

    def test_onset_is_clamped_at_the_floor(self):
        self.assertAlmostEqual(
            sustained_arc_onset_voltage(0.02, "bare-composite"),
            MINIMUM_ONSET_VOLTAGE_V,
            places=9,
        )

    def test_zero_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            sustained_arc_onset_voltage(0.0, "polyimide")

    def test_unknown_material_is_rejected(self):
        with self.assertRaises(ValueError):
            sustained_arc_onset_voltage(0.90, "unobtainium-tape")

    def test_non_string_material_is_rejected(self):
        with self.assertRaises(ValueError):
            sustained_arc_onset_voltage(0.90, 7)


class VoltageCriterionTests(unittest.TestCase):
    def test_low_voltage_satisfies_the_criterion(self):
        result = evaluate_voltage_criterion(30.0, 50.0)
        self.assertTrue(result["satisfied"])
        self.assertAlmostEqual(result["allowable_voltage_v"], 40.0, places=9)
        self.assertAlmostEqual(result["margin_v"], 10.0, places=9)

    def test_voltage_above_the_allowance_fails(self):
        self.assertFalse(evaluate_voltage_criterion(48.0, 50.0)["satisfied"])

    def test_voltage_exactly_at_the_allowance_passes(self):
        self.assertTrue(evaluate_voltage_criterion(40.0, 50.0)["satisfied"])

    def test_summed_worst_case_at_the_allowance_is_absorbed(self):
        # 33.6 V open circuit + 4.2 V cold rise + 2.2 V transient is exactly
        # 40 V physically, the allowance for a 50 V onset, but the running sum
        # lands one ULP above it in binary floating point.
        worst_case = worst_case_string_to_string_voltage(28.0, 1.2, 0.0025, -30.0, 20.0, 2.2)
        self.assertAlmostEqual(worst_case, 40.0, places=9)
        self.assertGreater(worst_case, 40.0)
        self.assertTrue(evaluate_voltage_criterion(worst_case, 50.0)["satisfied"])

    def test_zero_margin_fraction_uses_the_bare_onset(self):
        result = evaluate_voltage_criterion(49.0, 50.0, margin_fraction=0.0)
        self.assertTrue(result["satisfied"])
        self.assertAlmostEqual(result["allowable_voltage_v"], 50.0, places=9)

    def test_margin_fraction_of_one_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_voltage_criterion(10.0, 50.0, margin_fraction=1.0)

    def test_negative_worst_case_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_voltage_criterion(-1.0, 50.0)

    def test_zero_onset_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_voltage_criterion(10.0, 0.0)


class CurrentCriterionTests(unittest.TestCase):
    def test_low_available_current_satisfies_the_criterion(self):
        result = evaluate_current_criterion(0.1, 3)
        self.assertTrue(result["satisfied"])
        self.assertAlmostEqual(result["available_current_a"], 0.3, places=9)

    def test_parallel_strings_multiply_the_available_current(self):
        result = evaluate_current_criterion(0.2, 8)
        self.assertFalse(result["satisfied"])
        self.assertAlmostEqual(result["available_current_a"], 1.6, places=9)

    def test_summed_current_at_the_limit_is_absorbed(self):
        # Twenty 25 mA strings are exactly the 0.5 A limit physically; the
        # running sum lands one ULP above it.
        result = evaluate_current_criterion(0.025, 20)
        self.assertGreater(result["available_current_a"], SUSTAINING_CURRENT_LIMIT_A)
        self.assertTrue(result["satisfied"])

    def test_zero_parallel_strings_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_current_criterion(0.1, 0)

    def test_non_integer_string_count_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_current_criterion(0.1, 2.5)

    def test_negative_string_current_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_current_criterion(-0.1, 2)


class EvidenceTests(unittest.TestCase):
    def test_complete_evidence_has_no_gaps(self):
        self.assertEqual(missing_exemption_evidence({"evidence": FULL_EVIDENCE}), [])

    def test_missing_items_are_listed_in_contract_order(self):
        gaps = missing_exemption_evidence(
            {"evidence": ["conductor-gap-measurement", "string-current-capability"]}
        )
        self.assertEqual(
            gaps, ["worst-case-voltage-derivation", "insulation-material-record"]
        )

    def test_absent_evidence_key_reports_every_item(self):
        self.assertEqual(len(missing_exemption_evidence({})), len(REQUIRED_EVIDENCE_ITEMS))

    def test_evidence_names_are_case_insensitive(self):
        upper = [item.upper() for item in FULL_EVIDENCE]
        self.assertEqual(missing_exemption_evidence({"evidence": upper}), [])

    def test_non_sequence_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_exemption_evidence({"evidence": "worst-case-voltage-derivation"})

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_exemption_evidence(["evidence"])


class ExemptionDecisionTests(unittest.TestCase):
    def test_low_voltage_array_is_exempt(self):
        result = evaluate_secondary_arc_test_exemption(low_voltage_record())
        self.assertTrue(result["exemption_granted"])
        self.assertEqual(result["refusal_reasons"], [])
        self.assertEqual(result["required_actions"], [])
        self.assertAlmostEqual(result["onset_voltage_v"], 50.0, places=9)

    def test_high_voltage_array_is_refused(self):
        result = evaluate_secondary_arc_test_exemption(
            low_voltage_record(nominal_operating_v=100.0)
        )
        self.assertFalse(result["exemption_granted"])
        self.assertIn("worst-case-voltage-reaches-onset", result["refusal_reasons"])
        self.assertIn("run-secondary-arc-test-campaign", result["required_actions"])

    def test_high_current_array_is_refused(self):
        result = evaluate_secondary_arc_test_exemption(
            low_voltage_record(string_current_a=0.9, parallel_strings=4)
        )
        self.assertFalse(result["exemption_granted"])
        self.assertIn("available-current-can-sustain-an-arc", result["refusal_reasons"])

    def test_incomplete_evidence_is_refused(self):
        result = evaluate_secondary_arc_test_exemption(
            low_voltage_record(evidence=["conductor-gap-measurement"])
        )
        self.assertFalse(result["exemption_granted"])
        self.assertIn("exemption-evidence-incomplete", result["refusal_reasons"])
        self.assertIn("complete-exemption-evidence-package", result["required_actions"])

    def test_narrow_gap_can_flip_a_grant_to_a_refusal(self):
        granted = evaluate_secondary_arc_test_exemption(low_voltage_record())
        refused = evaluate_secondary_arc_test_exemption(
            low_voltage_record(conductor_gap_mm=0.20)
        )
        self.assertTrue(granted["exemption_granted"])
        self.assertFalse(refused["exemption_granted"])
        self.assertLess(refused["onset_voltage_v"], granted["onset_voltage_v"])

    def test_decision_rejects_missing_key(self):
        record = low_voltage_record()
        del record["conductor_gap_mm"]
        with self.assertRaises(ValueError):
            evaluate_secondary_arc_test_exemption(record)

    def test_decision_rejects_non_mapping_record(self):
        with self.assertRaises(ValueError):
            evaluate_secondary_arc_test_exemption("array-1")

    def test_actions_are_deduplicated(self):
        actions = required_actions_on_refusal(
            ["worst-case-voltage-reaches-onset", "available-current-can-sustain-an-arc"]
        )
        self.assertEqual(actions, ["run-secondary-arc-test-campaign"])

    def test_unknown_refusal_reason_is_rejected(self):
        with self.assertRaises(ValueError):
            required_actions_on_refusal(["cosmic-rays"])

    def test_empty_refusal_list_is_rejected(self):
        with self.assertRaises(ValueError):
            required_actions_on_refusal([])


if __name__ == "__main__":
    unittest.main()
