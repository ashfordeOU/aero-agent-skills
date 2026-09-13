#!/usr/bin/env python3
"""Contract test for the photovoltaic assembly continuity check (offline).

Walks the clause workflow step by step: the control-drawing circuit list
and the conditions it imposes, the probe technique and lead-resistance
handling, the referral of a reading back to the reference temperature,
the three readings a circuit can give, the coverage accounting against
the drawing, and the campaign verdict. This is the gate 3 review
evidence for the leaf.
"""

import copy
import unittest

from e2008_electrical_continuity_check_logic import (
    CIRCUIT_ABOVE_LIMIT,
    CIRCUIT_CONTINUOUS,
    CIRCUIT_NOT_EVALUATED,
    CIRCUIT_NOT_MEASURED,
    CIRCUIT_OPEN,
    CONDUCTOR_ALPHA_PER_K,
    CONTINUITY_NOT_EVALUATED,
    CONTINUITY_NOT_VERIFIED,
    CONTINUITY_VERIFIED,
    DEFAULT_CONTINUITY_CONDITIONS,
    FOUR_WIRE_REQUIRED_BELOW_OHM,
    circuit_coverage,
    effective_resistance_ohm,
    evaluate_circuit,
    evaluate_continuity_campaign,
    measurement_condition_findings,
    temperature_corrected_resistance,
    validate_continuity_conditions,
    validate_control_drawing,
)

CONDITIONS = dict(DEFAULT_CONTINUITY_CONDITIONS)

DRAWING = {
    "conditions": copy.deepcopy(CONDITIONS),
    "circuits": [
        {"id": "s1-string-return", "from": "j1-1", "to": "tb1-a", "max_resistance_ohm": 0.25},
        {"id": "s2-string-return", "from": "j1-2", "to": "tb1-b", "max_resistance_ohm": 0.25},
        {"id": "shunt-sense", "from": "j2-1", "to": "tb2-a", "max_resistance_ohm": 2.0},
    ],
}


def _measurement(circuit_id, ohm, technique="four-wire", temperature_c=22.0,
                 current_a=0.1, **extra):
    record = {
        "circuit_id": circuit_id,
        "resistance_ohm": ohm,
        "probe_technique": technique,
        "temperature_c": temperature_c,
        "test_current_a": current_a,
    }
    record.update(extra)
    return record


SOUND_MEASUREMENTS = [
    _measurement("s1-string-return", 0.12),
    _measurement("s2-string-return", 0.13),
    _measurement("shunt-sense", 1.4),
]


class ConditionsTests(unittest.TestCase):
    def test_default_conditions_validate(self):
        self.assertIs(
            validate_continuity_conditions(copy.deepcopy(CONDITIONS)).get("conductor"),
            "copper",
        )

    def test_unknown_conductor_rejected(self):
        conditions = copy.deepcopy(CONDITIONS)
        conditions["conductor"] = "unobtainium"
        with self.assertRaises(ValueError):
            validate_continuity_conditions(conditions)

    def test_inverted_temperature_band_rejected(self):
        conditions = copy.deepcopy(CONDITIONS)
        conditions["temperature_band_c"] = (28.0, 18.0)
        with self.assertRaises(ValueError):
            validate_continuity_conditions(conditions)

    def test_reference_temperature_outside_band_rejected(self):
        conditions = copy.deepcopy(CONDITIONS)
        conditions["reference_temperature_c"] = 40.0
        with self.assertRaises(ValueError):
            validate_continuity_conditions(conditions)

    def test_zero_test_current_lower_edge_rejected(self):
        conditions = copy.deepcopy(CONDITIONS)
        conditions["test_current_band_a"] = (0.0, 1.0)
        with self.assertRaises(ValueError):
            validate_continuity_conditions(conditions)


class DrawingTests(unittest.TestCase):
    def test_sound_drawing_validates(self):
        self.assertEqual(len(validate_control_drawing(copy.deepcopy(DRAWING))["circuits"]), 3)

    def test_empty_circuit_list_rejected(self):
        drawing = copy.deepcopy(DRAWING)
        drawing["circuits"] = []
        with self.assertRaises(ValueError):
            validate_control_drawing(drawing)

    def test_duplicate_circuit_id_rejected(self):
        drawing = copy.deepcopy(DRAWING)
        drawing["circuits"][1]["id"] = "s1-string-return"
        with self.assertRaises(ValueError):
            validate_control_drawing(drawing)

    def test_circuit_joined_to_itself_rejected(self):
        drawing = copy.deepcopy(DRAWING)
        drawing["circuits"][0]["to"] = drawing["circuits"][0]["from"]
        with self.assertRaises(ValueError):
            validate_control_drawing(drawing)

    def test_non_positive_limit_rejected(self):
        drawing = copy.deepcopy(DRAWING)
        drawing["circuits"][0]["max_resistance_ohm"] = 0.0
        with self.assertRaises(ValueError):
            validate_control_drawing(drawing)


class TemperatureCorrectionTests(unittest.TestCase):
    def test_reading_at_reference_is_unchanged(self):
        self.assertAlmostEqual(
            temperature_corrected_resistance(0.2, 22.0, 22.0, "copper"), 0.2, places=9
        )

    def test_warm_reading_corrects_downward(self):
        warm = temperature_corrected_resistance(0.2, 32.0, 22.0, "copper")
        self.assertAlmostEqual(warm, 0.2 / (1.0 + 0.00393 * 10.0), places=12)

    def test_cold_reading_corrects_upward(self):
        cold = temperature_corrected_resistance(0.2, 12.0, 22.0, "copper")
        self.assertAlmostEqual(cold, 0.2 / (1.0 - 0.00393 * 10.0), places=12)

    def test_aluminium_coefficient_differs_from_copper(self):
        aluminium = temperature_corrected_resistance(0.2, 32.0, 22.0, "aluminium")
        copper = temperature_corrected_resistance(0.2, 32.0, 22.0, "copper")
        self.assertNotAlmostEqual(aluminium, copper, places=9)
        self.assertGreater(CONDUCTOR_ALPHA_PER_K["aluminium"], CONDUCTOR_ALPHA_PER_K["copper"])

    def test_correction_beyond_linear_model_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_resistance(0.2, -300.0, 22.0, "copper")

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_resistance(-0.1, 22.0, 22.0, "copper")


class ProbeTests(unittest.TestCase):
    def test_four_wire_reading_passes_through(self):
        reading = _measurement("s1-string-return", 0.12)
        self.assertAlmostEqual(effective_resistance_ohm(reading, 0.25), 0.12, places=12)

    def test_two_wire_reading_has_leads_subtracted(self):
        reading = _measurement(
            "shunt-sense", 1.5, technique="two-wire", lead_resistance_ohm=0.1
        )
        self.assertAlmostEqual(effective_resistance_ohm(reading, 2.0), 1.4, places=12)

    def test_two_wire_without_leads_on_a_low_limit_rejected(self):
        reading = _measurement("s1-string-return", 0.12, technique="two-wire")
        self.assertLess(0.25, FOUR_WIRE_REQUIRED_BELOW_OHM)
        with self.assertRaises(ValueError):
            effective_resistance_ohm(reading, 0.25)

    def test_lead_resistance_above_the_reading_rejected(self):
        reading = _measurement(
            "shunt-sense", 1.5, technique="two-wire", lead_resistance_ohm=2.0
        )
        with self.assertRaises(ValueError):
            effective_resistance_ohm(reading, 2.0)

    def test_unknown_probe_technique_rejected(self):
        reading = _measurement("shunt-sense", 1.5, technique="guesswork")
        with self.assertRaises(ValueError):
            effective_resistance_ohm(reading, 2.0)


class ConditionFindingTests(unittest.TestCase):
    def test_in_band_reading_raises_no_finding(self):
        self.assertEqual(
            measurement_condition_findings(
                _measurement("shunt-sense", 1.4), CONDITIONS, 2.0
            ),
            [],
        )

    def test_out_of_band_test_current_is_reported(self):
        reading = _measurement("shunt-sense", 1.4, current_a=5.0)
        findings = measurement_condition_findings(reading, CONDITIONS, 2.0)
        self.assertTrue(any("test current" in item for item in findings))

    def test_out_of_band_temperature_is_reported(self):
        reading = _measurement("shunt-sense", 1.4, temperature_c=55.0)
        findings = measurement_condition_findings(reading, CONDITIONS, 2.0)
        self.assertTrue(any("temperature" in item for item in findings))


class CircuitVerdictTests(unittest.TestCase):
    def test_circuit_under_limit_is_continuous(self):
        record = evaluate_circuit(DRAWING["circuits"][0], SOUND_MEASUREMENTS[0], CONDITIONS)
        self.assertEqual(record["verdict"], CIRCUIT_CONTINUOUS)
        self.assertTrue(record["conducts"])

    def test_circuit_exactly_on_the_limit_is_continuous(self):
        record = evaluate_circuit(
            DRAWING["circuits"][0], _measurement("s1-string-return", 0.25), CONDITIONS
        )
        self.assertAlmostEqual(record["corrected_resistance_ohm"], 0.25, places=9)
        self.assertEqual(record["verdict"], CIRCUIT_CONTINUOUS)

    def test_circuit_over_limit_still_conducts(self):
        record = evaluate_circuit(
            DRAWING["circuits"][0], _measurement("s1-string-return", 0.9), CONDITIONS
        )
        self.assertEqual(record["verdict"], CIRCUIT_ABOVE_LIMIT)
        self.assertTrue(record["conducts"])

    def test_no_instrument_reading_is_an_open_circuit(self):
        record = evaluate_circuit(
            DRAWING["circuits"][0], _measurement("s1-string-return", None), CONDITIONS
        )
        self.assertEqual(record["verdict"], CIRCUIT_OPEN)
        self.assertFalse(record["conducts"])

    def test_reading_above_the_open_threshold_is_an_open_circuit(self):
        record = evaluate_circuit(
            DRAWING["circuits"][0], _measurement("s1-string-return", 5.0e7), CONDITIONS
        )
        self.assertEqual(record["verdict"], CIRCUIT_OPEN)

    def test_unprobed_circuit_is_not_measured(self):
        record = evaluate_circuit(DRAWING["circuits"][0], None, CONDITIONS)
        self.assertEqual(record["verdict"], CIRCUIT_NOT_MEASURED)
        self.assertIsNone(record["conducts"])

    def test_unresolvable_two_wire_reading_is_not_evaluated(self):
        record = evaluate_circuit(
            DRAWING["circuits"][0],
            _measurement("s1-string-return", 0.12, technique="two-wire"),
            CONDITIONS,
        )
        self.assertEqual(record["verdict"], CIRCUIT_NOT_EVALUATED)
        self.assertTrue(record["findings"])


class CoverageTests(unittest.TestCase):
    def test_full_coverage_is_complete(self):
        coverage = circuit_coverage(copy.deepcopy(DRAWING), copy.deepcopy(SOUND_MEASUREMENTS))
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["measured_count"], 3)

    def test_unprobed_circuit_is_listed(self):
        coverage = circuit_coverage(
            copy.deepcopy(DRAWING), copy.deepcopy(SOUND_MEASUREMENTS[:2])
        )
        self.assertEqual(coverage["unmeasured_ids"], ["shunt-sense"])
        self.assertFalse(coverage["complete"])

    def test_repeated_reading_is_listed(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements.append(_measurement("s1-string-return", 0.19))
        coverage = circuit_coverage(copy.deepcopy(DRAWING), measurements)
        self.assertEqual(coverage["duplicate_ids"], ["s1-string-return"])

    def test_reading_on_an_undeclared_circuit_is_listed(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements.append(_measurement("s9-phantom", 0.19))
        coverage = circuit_coverage(copy.deepcopy(DRAWING), measurements)
        self.assertEqual(coverage["unknown_ids"], ["s9-phantom"])


class CampaignTests(unittest.TestCase):
    def _campaign(self, measurements):
        return {
            "drawing": copy.deepcopy(DRAWING),
            "measurements": copy.deepcopy(measurements),
        }

    def test_sound_campaign_is_verified(self):
        result = evaluate_continuity_campaign(self._campaign(SOUND_MEASUREMENTS))
        self.assertEqual(result["verdict"], CONTINUITY_VERIFIED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["failing_ids"], [])

    def test_open_circuit_fails_the_campaign(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements[1]["resistance_ohm"] = None
        result = evaluate_continuity_campaign(self._campaign(measurements))
        self.assertEqual(result["verdict"], CONTINUITY_NOT_VERIFIED)
        self.assertIn("s2-string-return", result["failing_ids"])

    def test_degraded_joint_fails_the_campaign(self):
        measurements = copy.deepcopy(SOUND_MEASUREMENTS)
        measurements[0]["resistance_ohm"] = 0.8
        result = evaluate_continuity_campaign(self._campaign(measurements))
        self.assertEqual(result["verdict"], CONTINUITY_NOT_VERIFIED)
        self.assertFalse(result["compliant"])

    def test_missing_circuit_leaves_the_campaign_unevaluated(self):
        result = evaluate_continuity_campaign(self._campaign(SOUND_MEASUREMENTS[:2]))
        self.assertEqual(result["verdict"], CONTINUITY_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])

    def test_verdicts_are_grouped_for_reporting(self):
        result = evaluate_continuity_campaign(self._campaign(SOUND_MEASUREMENTS))
        self.assertEqual(sorted(result["grouped_by_verdict"]), [CIRCUIT_CONTINUOUS])

    def test_campaign_without_measurements_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_campaign({"drawing": copy.deepcopy(DRAWING)})

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity_campaign("all circuits buzzed out fine")


if __name__ == "__main__":
    unittest.main()
